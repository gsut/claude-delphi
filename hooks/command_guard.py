# Claude Code PreToolUse (Bash | PowerShell) hook: enforces mechanical rules before a shell command runs.
#   1. No inline Python on the command line (python -c / -Ic, python -, python <<, a bare python reading a pipe): write the
#      script to a file, then run it. Reason: an inline script cannot be reviewed or re-run; a script file can.
#   2. No "sed -i" / "perl -i" on protected files (Pascal / DFM / scripts / docs): Git Bash sed -i strips CRs from CRLF.
#   3. No shell redirection (>, >>, >|, &>; quoted or not) or tee into a protected file, and in PowerShell no Set-Content /
#      Add-Content / Out-File / Tee-Object / [IO.File]::Write... on one: breaks the ANSI code page and CRLF line endings.
#   4. No database connection as a user with write access (Claude works with a read-only user).
#   5. No GitHub CLI command that writes to GitHub (creating / editing / deleting releases, PRs, issues, repos, writing
#      gh api calls ...): like Git, gh is read-only for Claude. Catches gh.exe called by full path too, which the
#      "Bash(gh ...)" deny rules in settings.json do not. Off with "forbid_gh_write": false.
#   6. Read-only agents ("readonly_agents"; the hook input's agent_type, present when a sub-agent calls the tool): no
#      command substitution, no redirection into a file, no program that writes or runs others (rm, cp, xargs, bash,
#      awk ...), only reading git subcommands without --output / grep -O / --ext-diff, no find -delete / -exec / -fprint,
#      only "sed -n <range>p", no sort -o, no rg --pre, no database client option that writes a local file, python only
#      for the read-only tools; the PowerShell tool not at all. A trip wire against habit, not a security boundary:
#      unlisted programs are allowed.
# All rules are patterns on the command text, a trip wire against habit for the main session too: a program that writes by
# itself (cp, a script), a nested shell, a target held in a variable or a connection with implicit credentials pass.
# Fails closed: if the hook input cannot be read, the settings file exists but cannot be read, or the hook itself fails
# on a command, the command is refused.
# Settings: $CLAUDE_PROJECT_DIR/.claude/claude-delphi.json (defaults below if missing). Input: hook JSON on stdin.
# Output: permissionDecision = deny when a rule is broken; otherwise silent exit.
import json
import os
import re
import shlex
import sys

sys.dont_write_bytecode = True   # no __pycache__ next to the hooks in the user's project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python -I leaves the script's folder off sys.path
import hook_common  # noqa: E402

SHELL_TOOLS = ("Bash", "PowerShell")
DEFAULTS = {
    "forbid_gh_write": True,
    "protected_extensions": [".pas", ".dfm", ".dpr", ".dproj", ".inc", ".py", ".md"],
    "forbid_inline_python": True,
    "write_db_users": [],
    "scripts_dir": "scripts/",
    "readonly_agents": ["scope-counter", "devils-advocate", "closeout-auditor"],
}


PY_NAME = re.compile(r"^(?:.*[/\\])?(?:pythonw?[\d.]*|pyw?)(?:\.exe)?$", re.I)
TAKES_VALUE = {"-X", "-W"}                      # interpreter options followed by a value


def split_command(command):
    # Splits on ; & | and newlines; text inside single / double quotes is not a split point
    # (otherwise  sed -i 's/a/b/; s/c/d/' x.pas  separates "sed -i" from the file name).
    parts, part, quote, i = [], [], None, 0
    while i < len(command):
        c = command[i]
        if quote:
            if c == "\\" and quote == '"' and i + 1 < len(command):
                part.append(command[i:i + 2])
                i += 2
                continue
            if c == quote:
                quote = None
            part.append(c)
        elif c in "'\"":
            quote = c
            part.append(c)
        elif c == "\\" and i + 1 < len(command):
            part.append(command[i:i + 2])
            i += 2
            continue
        elif c in ";&|\n" and not ((c == "|" and part[-1:] == [">"]) or
                                   (c == "&" and (part[-1:] == [">"] or command[i + 1:i + 2] == ">"))):
            # >| (clobber), >&2 / 2>&1 (fd copy) and &> (both streams) are redirections, not command separators
            parts.append("".join(part))
            part = []
        else:
            part.append(c)
        i += 1
    parts.append("".join(part))
    return [p.strip() for p in parts if p.strip()]


def extension_pattern(extensions, at_end):
    body = "|".join(re.escape(e.lstrip(".")) for e in extensions)
    return re.compile(r"\.(%s)%s" % (body, "$" if at_end else r"\b"), re.I)


PS_WRITE = re.compile(r"(?:^|[\s;|(])(?:Set-Content|Add-Content|Out-File|Tee-Object|Clear-Content|sc|ac)\b"
                      r"|\[(?:System\.)?IO\.File\]::(?:Write|Append|Create)", re.I)


def without_quotes(part):
    # blanks out quoted strings (a '>' or a file name inside quotes is not a redirection)
    return re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", "''", part)


def words_of(part):
    try:
        return shlex.split(part, posix=True)
    except ValueError:
        return part.split()


def redirect_targets(part):
    """file targets of >, >>, >|, &>, 2> outside quotes; a quoted target is unquoted ("My Unit.pas"); fd copies (>&2) and
    process substitution >( ) are not files"""
    targets, i, quote, n = [], 0, None, len(part)
    while i < n:
        c = part[i]
        if quote:
            if c == "\\" and quote == '"':
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"":
            quote = c
        elif c == "\\":
            i += 1
        elif c == ">":
            j = i + 1
            if j < n and part[j] in ">|":
                j += 1
            if j < n and part[j] in "&(":
                i = j + 1
                continue
            while j < n and part[j] in " \t":
                j += 1
            word = []
            while j < n and part[j] not in " \t;&|<>()":
                if part[j] in "'\"":
                    end = part.find(part[j], j + 1)
                    end = n if end < 0 else end
                    word.append(part[j + 1:end])
                    j = end + 1
                    continue
                word.append(part[j])
                j += 1
            targets.append("".join(word))
            i = j
            continue
        i += 1
    return targets


def writes_protected(part, protected_at_end, protected, powershell):
    for target in redirect_targets(part):
        if protected_at_end.search(target):
            return target
    words = words_of(part)
    for i, w in enumerate(words):
        if program(w) in ("tee", "tee-object"):
            for a in words[i + 1:]:
                if not a.startswith("-") and protected_at_end.search(a):
                    return a
    if powershell and PS_WRITE.search(part) and protected.search(part):
        return protected.search(part).group(0)
    return None


def in_place_edit(part):
    """sed -i / --in-place (also -Ei, -i.bak, a full path to sed) or perl -i / -pi / -0pi before the script name"""
    words = words_of(part)
    for i, w in enumerate(words):
        name = program(w)
        if name in ("sed", "gsed"):
            for a in words[i + 1:]:
                if a == "--in-place" or a.startswith("--in-place="):
                    return True
                if a.startswith("-") and not a.startswith("--") and "i" in a[1:].split(".")[0]:
                    return True
        elif name == "perl":
            for a in words[i + 1:]:
                if not a.startswith("-"):
                    break                       # the script name: what follows belongs to the script
                if re.match(r"^-[A-Za-z0-9]*i", a):
                    return True
    return False


def inline_python(part):
    words = words_of(part.replace("<", " <"))
    for i, w in enumerate(words):
        if not PY_NAME.match(w.strip("\"'(`")):
            continue
        if i == len(words) - 1:
            return i == 0                       # a bare python as the command reads its script from a pipe / stdin
        j = i + 1
        while j < len(words):
            t = words[j]
            if t == "-" or t.startswith("<"):
                return True
            if t.startswith("--") or not t.startswith("-"):
                break                           # long option (--version) or the script path: allowed
            cluster, j = t[1:], j + 1
            for k, ch in enumerate(cluster):
                if ch == "c":
                    return True                 # -c, -Ic, -uc, -c"print(1)"
                if ch == "m":
                    return False                # -m module: allowed
                if ch in "XW":
                    if k == len(cluster) - 1:
                        j += 1                  # the value is the next word
                    break
    return False


def db_user_pattern(users):
    # Database client independent: catches the user name in the usual places of command line clients and connection strings.
    #   options:  -U name (psql, sqlcmd), -u name / --user=name / --username name (mysql, mariadb), -user name (Firebird isql)
    #   env vars: PGUSER=, MYSQL_USER=, ISC_USER=, SQLCMDUSER=
    #   strings:  User ID=name / UID=name / User=name / user=name (ADO, ODBC, libpq conninfo, FireDAC)
    #   URLs:     scheme://name:password@host, name@host
    if not users:
        return None
    n = "(?:%s)" % "|".join(re.escape(u) for u in users)
    q = r"[\"']?"
    parts = [
        # -U / -u also at the end of a cluster of short options (psql -wU name)
        r"(?:^|[\s\"'])(?:-[A-Za-z]*[Uu]|--?user(?:name)?)(?:\s*=\s*|\s+|)" + q + n + r"(?![\w.-])",
        r"\b(?:PGUSER|MYSQL_USER|ISC_USER|SQLCMDUSER)\s*=\s*" + q + n + r"(?![\w.-])",
        r"\b(?:User\s*ID|UID|User|Username|User_Name)\s*=\s*" + q + n + r"(?![\w.-])",
        r"(?:^|[\s\"'/])" + n + r"(?::[^@\s/]*)?@",
    ]
    return re.compile("|".join(parts), re.I)


# GitHub CLI subcommands that write. None = every subcommand of the group writes.
GH_NAME = re.compile(r"^(?:.*[/\\])?gh(?:\.exe)?$", re.I)
GH_WRITES = {
    "release": {"create", "edit", "delete", "upload", "delete-asset"},
    "pr": {"create", "merge", "close", "reopen", "edit", "comment", "review", "ready", "checkout", "lock", "unlock",
           "update-branch", "revert"},
    "issue": {"create", "close", "reopen", "edit", "comment", "delete", "transfer", "lock", "unlock", "pin", "unpin",
              "develop"},
    "repo": {"create", "delete", "edit", "fork", "rename", "archive", "unarchive", "sync", "set-default", "deploy-key"},
    "workflow": {"run", "enable", "disable"},
    "run": {"rerun", "cancel", "delete"},
    "label": {"create", "edit", "delete", "clone"},
    "gist": {"create", "edit", "delete", "rename", "clone"},
    "variable": {"set", "delete"},
    "cache": {"delete"},
    "auth": {"login", "logout", "refresh", "token", "setup-git", "switch"},
    "config": {"set", "clear-cache"},
    "alias": {"set", "delete", "import"},
    "extension": {"install", "remove", "upgrade", "create", "exec"},
    "ssh-key": {"add", "delete"}, "gpg-key": {"add", "delete"},
    "secret": None, "codespace": None, "project": None,
}
GH_SUBGROUPS = {("repo", "deploy-key"): {"add", "delete"}}     # gh repo deploy-key list only reads
GH_VALUE_OPTIONS = {"-R", "--repo", "--hostname"}             # global options followed by a value
GH_API_WRITES = {"-f", "-F", "--field", "--raw-field", "--input"}


def gh_writes(part):
    words = words_of(part)
    for i, w in enumerate(words):
        if not GH_NAME.match(w):
            continue
        rest = [x for x in words[i + 1:] if x]
        if not rest:
            return False
        positional, skip = [], False             # group, subcommand ... without options (gh -R o/r pr create)
        for x in rest:
            if skip:
                skip = False
            elif x in GH_VALUE_OPTIONS:
                skip = True
            elif not x.startswith("-"):
                positional.append(x)
        group = positional[0] if positional else ""
        sub = positional[1] if len(positional) > 1 else ""
        if (group, sub) in GH_SUBGROUPS:
            return (positional[2] if len(positional) > 2 else "") in GH_SUBGROUPS[(group, sub)]
        if group == "api":
            for j, x in enumerate(rest):
                if x in GH_API_WRITES or any(x.startswith(o + "=") for o in GH_API_WRITES):
                    return True
                if x in ("-X", "--method") and j + 1 < len(rest) and rest[j + 1].upper() != "GET":
                    return True
                if (x.startswith("--method=") or (x.startswith("-X") and len(x) > 2)) and not x.upper().endswith("GET"):
                    return True
            return False
        if group in GH_WRITES:
            return GH_WRITES[group] is None or sub in GH_WRITES[group]
        return False
    return False


def check(command, s, powershell=False):
    protected = extension_pattern(s["protected_extensions"], at_end=False)
    protected_at_end = extension_pattern(s["protected_extensions"], at_end=True)
    for p in split_command(command):
        if s.get("forbid_gh_write", True) and gh_writes(p):
            return ("A GitHub CLI command that writes to GitHub is not allowed: gh is read-only for Claude (view / list, "
                    "gh api GET). Creating, editing, deleting and posting are done by the developer; describe what to do.")
        if s["forbid_inline_python"] and inline_python(p):
            return ("Inline Python on the command line is not allowed. Write the script to a .py file with Write (%s), "
                    "then run it by path. Use Edit / Write to change files and Read / Grep to read them." % s["scripts_dir"])
        if in_place_edit(p) and protected.search(p):
            return ("'sed -i' / 'perl -i' on a protected file is not allowed: Git Bash sed -i strips the CRs from CRLF line "
                    "endings. For Pascal / DFM use tools/pas_edit.py (keeps the code page and CRLF, refuses ambiguous "
                    "anchors); for .md and .py use Edit.")
        target = writes_protected(p, protected_at_end, protected, powershell)
        if target:
            return ("Writing to a protected file with shell redirection / tee / a PowerShell write cmdlet is not allowed: "
                    "target '%s'. The Pascal / DFM "
                    "code page and CRLF would break: use tools/pas_edit.py for Pascal / DFM; .md and .py change only "
                    "through Edit / Write. Use a .txt file for temporary output." % target)
    pattern = db_user_pattern(s["write_db_users"])
    if pattern and pattern.search(command):
        return ("Connecting to the database as a user with write access is not allowed: Claude's access is read-only. "
                "Prepare data or schema changes as a script for the developer to run.")
    return None


# --- Read-only agents (rule 6) ---------------------------------------------------------------------------------------
# A trip wire against habit, not a security boundary: it refuses the usual ways a shell command writes, but a program that
# is not listed can still write. Unlisted programs are allowed so that ordinary reading (cd, grep, sort | uniq, sed -n,
# for loops) keeps working.
FD_COPY = re.compile(r"\d*>&\d+|&>>?\s*/dev/null|\d*>>?\s*/dev/null")     # 2>&1, >&2, &>/dev/null, 2>/dev/null
SUBSTITUTION = re.compile(r"\$\(|`|<\(|>\(")
ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*=")
KEYWORDS = {"if", "then", "else", "elif", "do", "while", "until", "!", "{", "(", "time"}
WRITERS = {"rm", "rmdir", "mv", "cp", "touch", "mkdir", "dd", "truncate", "ln", "chmod", "chown", "install", "patch",
           "tee", "xargs", "eval", "exec", "env", "command", "bash", "sh", "zsh", "cmd", "powershell", "pwsh", "awk",
           "gawk", "perl", "ruby", "node", "curl", "wget", "unzip", "tar", "source", "."}
GIT_READ = {"log", "show", "diff", "blame", "grep", "ls-files", "status", "rev-parse", "cat-file", "shortlog", "describe",
            "ls-tree", "rev-list", "merge-base", "name-rev", "show-ref", "hash-object", "version", "help"}
GIT_WRITE_OPTIONS = ("--output", "-O", "--open-files-in-pager", "--ext-diff", "-w", "--write")
FIND_WRITE = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls"}
DB_CLIENTS = {"psql", "sqlcmd", "mysql", "mariadb", "isql", "isql-fb"}
DB_WRITE_OPTIONS = ("-o", "--output", "-L", "--log-file", "--tee", "-output")
PSQL_META = re.compile(r"\\(o|copy|!|w|g\s)")
READ_ONLY_SCRIPTS = {"diff_routines.py", "pas_callers.py", "pascal_lex.py", "dfm_field_check.py", "dfm_field_usage.py",
                     "dfm_text_check.py", "closeout_check.py"}
SED_PRINT = re.compile(r"^\d+(,(\d+|\$))?p$|^\$p$")


def program(word):
    name = re.split(r"[/\\]", word.lstrip("("))[-1].lower()
    return name[:-4] if name.endswith(".exe") else name


def has_option(args, options):
    for a in args:
        for o in options:
            if a == o or a.startswith(o + "=") or (o.startswith("-") and not o.startswith("--") and len(o) == 2
                                                    and a.startswith(o) and not a.startswith("--")):
                return o
    return None


def readonly_part(part):
    """reason this part of a command may write, or None"""
    # /dev/null and fd copies were removed before splitting, so any '>' left outside quotes is a redirection into a file
    # (also "grep x>out.txt" into any file, not only a protected one)
    if ">" in without_quotes(part):
        return "output redirection into a file"
    try:
        words = shlex.split(part, posix=True)
    except ValueError:
        return "the command cannot be parsed (unbalanced quotes)"
    while words and (words[0] in KEYWORDS or words[0].strip("(") == ""):
        words = words[1:]
    if not words:
        return None
    if ASSIGNMENT.match(words[0]):
        return "a variable assignment in front of a command (%s)" % words[0].split("=")[0]
    name, args = program(words[0]), words[1:]
    if name in WRITERS:
        return "'%s' can write or run other commands" % name
    if name == "git":
        while args and args[0].startswith("-"):
            if args[0] in ("-c", "-C") or args[0].startswith("--exec-path"):
                return "git option %s" % args[0]
            args = args[1:]
        sub = args[0] if args else ""
        if sub not in GIT_READ:
            return "'git %s' is not a reading git command" % sub
        if sub == "hash-object" and has_option(args, ("-w",)):
            return "'git hash-object -w' writes to the repository"
        o = has_option(args[1:], [x for x in GIT_WRITE_OPTIONS if x not in ("-w", "--write")])
        if o and not (o == "-O" and sub != "grep"):
            return "git option %s writes a file or runs a program" % o
    elif name == "find":
        hit = next((a for a in args if a in FIND_WRITE), None)
        if hit:
            return "find %s writes or runs a program" % hit
    elif name == "sed":
        scripts = [a for a in args if not a.startswith("-")][:1]
        if "-n" not in args or has_option(args, ("-i", "--in-place")) or not all(SED_PRINT.match(x) for x in scripts):
            return "only 'sed -n <from>,<to>p <file>' is allowed (use Read for anything else)"
    elif name == "sort":
        if has_option(args, ("-o", "--output")):
            return "sort -o writes a file"
    elif name == "uniq":
        if len([a for a in args if not a.startswith("-")]) > 1:
            return "uniq with two file names writes the second"
    elif name in ("rg", "ripgrep"):
        if has_option(args, ("--pre",)):
            return "rg --pre runs a program"
    elif name in DB_CLIENTS:
        o = has_option(args, DB_WRITE_OPTIONS)
        if o:
            return "%s %s writes a local file" % (name, o)
        if PSQL_META.search(part):
            return "a psql meta-command that writes or runs a program (\\o, \\copy, \\!, \\w, \\g file)"
    elif PY_NAME.match(name):
        i = 0
        while i < len(args) and args[i].startswith("-"):
            if args[i] in ("-m", "-c", "-"):
                return "python %s" % args[i]
            i += 2 if args[i] in TAKES_VALUE else 1
        script = re.split(r"[/\\]", args[i])[-1] if i < len(args) else ""
        if script not in READ_ONLY_SCRIPTS:
            return "python may only run the read-only tools (%s)" % ", ".join(sorted(READ_ONLY_SCRIPTS))
    return None


def check_readonly(command):
    t = command
    # single-quoted text is never expanded; $( ) and backticks inside double quotes are
    if SUBSTITUTION.search(re.sub(r"'[^']*'", "''", t)):
        return "command substitution ($( ), backticks, <( ), >( )) is not allowed"
    t = FD_COPY.sub(" ", t)
    for p in split_command(t):
        reason = readonly_part(p)
        if reason:
            return reason
    return None


def readonly_agent(data, s):
    agent = data.get("agent_type") or ""
    names = s.get("readonly_agents") or []
    # a plugin agent arrives as "plugin:name"
    return agent if agent and (agent in names or agent.split(":")[-1] in names) else None


def decide(data, s):
    command = (data.get("tool_input") or {}).get("command") or ""
    powershell = data.get("tool_name") == "PowerShell"
    reason = check(command, s, powershell)
    if reason:
        return reason
    agent = readonly_agent(data, s)
    if agent:
        if powershell:
            return ("Read-only agent '%s': the PowerShell tool is not checked by rule 6; use Read / Grep / Glob or Bash."
                    % agent)
        reason = check_readonly(command)
        if reason:
            return ("Read-only agent '%s': %s. This agent reads and reports; it does not change files. Use Read / Grep / "
                    "Glob, or a simpler reading command; if something must be written, say so in the report." % (agent, reason))
    return None


def main():
    try:
        data = hook_common.read_input()
    except ValueError as e:                     # fail closed: the hook is only wired to shell tools
        data, reason = None, "command_guard.py could not read the hook input (%s); the command was not checked." % e
    else:
        if data.get("tool_name") not in SHELL_TOOLS:
            return 0
        s, problem = hook_common.load_settings(DEFAULTS)
        try:
            reason = ("The settings file cannot be used, so the command was not checked: %s. Fix it with Edit." % problem
                      if problem else decide(data, s))
        except Exception as e:                  # a guard that crashes must not let the command through unchecked
            reason = ("command_guard.py could not check this command (%s: %s). Write it more simply, or report the error "
                      "to the developer." % (type(e).__name__, e))
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
