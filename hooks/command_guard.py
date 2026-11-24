# Claude Code PreToolUse (Bash) hook: enforces mechanical rules before a shell command runs.
#   1. No inline Python on the command line (python -c, python -, python <<): write the script to a file, then run it.
#      Reason: an inline script cannot be reviewed or re-run; a script file can.
#   2. No "sed -i" / "perl -i" on protected files (Pascal / DFM / scripts / docs): Git Bash sed -i strips CRs from CRLF.
#   3. No shell redirection (>, >>, &>) or tee into a protected file: breaks the ANSI code page and CRLF line endings.
#   4. No database connection as a user with write access (Claude works with a read-only user).
#   5. No GitHub CLI command that writes to GitHub (creating / editing / deleting releases, PRs, issues, repos, writing
#      gh api calls ...): like Git, gh is read-only for Claude. Catches gh.exe called by full path too, which the
#      "Bash(gh ...)" deny rules in settings.json do not. Off with "forbid_gh_write": false.
# Settings: $CLAUDE_PROJECT_DIR/.claude/claude-delphi.json (defaults below if missing). Input: hook JSON on stdin.
# Output: permissionDecision = deny when a rule is broken; otherwise silent exit.
import json
import os
import re
import shlex
import sys

DEFAULTS = {
    "forbid_gh_write": True,
    "protected_extensions": [".pas", ".dfm", ".dpr", ".dproj", ".inc", ".py", ".md"],
    "forbid_inline_python": True,
    "write_db_users": [],
    "scripts_dir": "scripts/",
}


def settings():
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    s = dict(DEFAULTS)
    try:
        with open(os.path.join(root, ".claude", "claude-delphi.json"), encoding="utf-8") as f:
            s.update(json.load(f))
    except (OSError, ValueError):
        pass
    return s


PY_NAME = re.compile(r"^(?:.*[/\\])?(?:python[\d.]*|py)(?:\.exe)?$", re.I)
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
        elif c in ";&|\n":
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


REDIRECT = re.compile(r"(?:^|[\s;&|(])(?:\d|&)?>{1,2}\s*([^\s;&|<>()]+)")
TEE = re.compile(r"(?:^|[\s|])tee\s+(?:-\S+\s+)*([^\s;&|<>()]+)")
IN_PLACE = re.compile(r"(^|\s)(sed\s(.*\s)?(-[A-Za-z]*i|--in-place)|perl\s(.*\s)?-[A-Za-z]*i)", re.I)


def without_quotes(part):
    # blanks out quoted strings (a '>' or a file name inside quotes is not a redirection)
    return re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", "''", part)


def writes_protected(part, protected_at_end):
    t = without_quotes(part)
    for m in list(REDIRECT.finditer(t)) + list(TEE.finditer(t)):
        if protected_at_end.search(m.group(1).strip("\"'")):
            return m.group(1)
    return None


def inline_python(part):
    words = part.replace("(", " ").replace("`", " ").split()
    for i, w in enumerate(words):
        if not PY_NAME.match(w.strip("\"'")):
            continue
        j = i + 1
        while j < len(words):
            t = words[j]
            if t == "-c" or t == "-" or t.startswith("<<") or t == "<":
                return True
            if t in TAKES_VALUE:
                j += 2
                continue
            if t.startswith("-") and t != "-m":
                j += 1
                continue
            break                               # script path or -m module: allowed
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
        r"(?:^|[\s\"'])(?:-U|-u|--?user(?:name)?)(?:\s*=\s*|\s+|)" + q + n + r"(?![\w.-])",
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
           "update-branch"},
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
    "secret": None, "codespace": None, "project": None,
}
GH_API_WRITES = {"-f", "-F", "--field", "--raw-field", "--input"}


def gh_writes(part):
    try:
        words = shlex.split(part, posix=True)
    except ValueError:
        words = part.split()
    for i, w in enumerate(words):
        if not GH_NAME.match(w):
            continue
        rest = [x for x in words[i + 1:] if x]
        if not rest:
            return False
        group = rest[0]
        sub = next((x for x in rest[1:] if not x.startswith("-")), "")
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


def check(command, s):
    protected = extension_pattern(s["protected_extensions"], at_end=False)
    protected_at_end = extension_pattern(s["protected_extensions"], at_end=True)
    for p in split_command(command):
        if s.get("forbid_gh_write", True) and gh_writes(p):
            return ("A GitHub CLI command that writes to GitHub is not allowed: gh is read-only for Claude (view / list, "
                    "gh api GET). Creating, editing, deleting and posting are done by the developer; describe what to do.")
        if s["forbid_inline_python"] and inline_python(p):
            return ("Inline Python on the command line is not allowed. Write the script to a .py file with Write (%s), "
                    "then run it by path. Use Edit / Write to change files and Read / Grep to read them." % s["scripts_dir"])
        if IN_PLACE.search(p) and protected.search(p):
            return ("'sed -i' / 'perl -i' on a protected file is not allowed: Git Bash sed -i strips the CRs from CRLF line "
                    "endings. For Pascal / DFM use tools/pas_edit.py (keeps the code page and CRLF, refuses ambiguous "
                    "anchors); for .md and .py use Edit.")
        target = writes_protected(p, protected_at_end)
        if target:
            return ("Writing to a protected file with shell redirection / tee is not allowed: target '%s'. The Pascal / DFM "
                    "code page and CRLF would break: use tools/pas_edit.py for Pascal / DFM; .md and .py change only "
                    "through Edit / Write. Use a .txt file for temporary output." % target)
    pattern = db_user_pattern(s["write_db_users"])
    if pattern and pattern.search(command):
        return ("Connecting to the database as a user with write access is not allowed: Claude's access is read-only. "
                "Prepare data or schema changes as a script for the developer to run.")
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    reason = check(command, settings())
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
