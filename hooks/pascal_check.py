# Claude Code hook for Pascal / DFM files: mechanical rules for files that were just changed.
#   PostToolUse (Write | Edit | Bash) reports, PreToolUse (Write | Edit) only takes a snapshot of the file it is about to
#   change, so the report can compare with the file as it was right before the tool ran.
#   1. Line endings: CRLF only (no newly added bare LF).
#   2. Encoding: if sources use a single-byte ANSI code page (cp1252, cp1254, cp1251 ...), a file saved as UTF-8 is an error.
#   3. Project-specific forbidden patterns ("forbidden_patterns" in the settings; e.g. BoolToStr(x, True)).
#   4. If a signature pattern is set: two consecutive comment lines must not both end with today's signature
#      (the signature belongs on the last line of an explanation only).
#   5. A binary DFM among the changed files is reported (it cannot be read or edited as text; ask the developer to convert it).
# Only NEW violations are reported. The baseline is, in this order: the PreToolUse snapshot (Write / Edit); else the
# committed version as Git would check it out (`git cat-file --filters`: .gitattributes eol=crlf / core.autocrlf
# applied); a committed version without any CR (a repository that stores LF and converts nothing) counts as CRLF, since
# the working copy of a Delphi source is CRLF. After Bash: the Pascal files that `git status` lists anywhere in the
# repository (any letter case) and that changed in the last 10 minutes.
# The hook never touches the file; it only reports (PostToolUse "block" = feedback to Claude). An unreadable settings file
# or hook input is reported, not ignored. Settings: $CLAUDE_PROJECT_DIR/.claude/claude-delphi.json.
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python -I leaves the script's folder off sys.path
import hook_common  # noqa: E402

DEFAULTS = {
    "pascal_extensions": [".pas", ".dfm", ".dpr", ".inc"],
    "source_encoding": "cp1252",
    "forbidden_patterns": [],        # [{"pattern": "<regex>", "message": "..."}]
    "signature_pattern": "",         # e.g. "[A-Z]{2,4} - {date}"; {date} = today in date_format
    "date_format": "%d.%m.%Y",
}
WINDOW_SEC = 600                     # after Bash: files changed in the last 10 minutes
SNAPSHOT_DIR = os.path.join(tempfile.gettempdir(), "claude-delphi-pascal-check")
SNAPSHOT_MAX_AGE = 86400             # snapshots whose PostToolUse never came are removed after a day
CR, LF = 13, 10


def git(args, cwd):
    try:
        return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, timeout=20).stdout
    except Exception:
        return b""


def bare_lf(data):
    return data.count(bytes([LF])) - data.count(bytes([CR, LF]))


def is_utf8(data):
    if data.startswith(bytes([0xEF, 0xBB, 0xBF])):
        return True
    if all(b < 128 for b in data):
        return False
    try:
        data.decode("utf-8")
        return True                  # non-ASCII bytes and all valid UTF-8: not a single-byte code page
    except UnicodeDecodeError:
        return False


def double_signature(data, s):
    if not s["signature_pattern"]:
        return []
    today = re.escape(datetime.date.today().strftime(s["date_format"]))
    sig = re.compile((s["signature_pattern"].replace("{date}", today) + r"\s*[})*]*\s*$").encode("utf-8"))
    comment = re.compile(rb"^\s*(//|\{|\(\*)")
    lines = data.split(bytes([LF]))
    found = []
    for i in range(1, len(lines)):
        a, b = lines[i - 1].rstrip(), lines[i].rstrip()
        if comment.match(a) and comment.match(b) and sig.search(a) and sig.search(b):
            found.append(i)
    return found


def git_root(cwd):
    r = git(["rev-parse", "--show-toplevel"], cwd).decode("utf-8", "replace").strip()
    return r or cwd


# --- snapshot taken in PreToolUse (Write / Edit) ---
def snapshot_path(data):
    sid, tid = data.get("session_id"), data.get("tool_use_id")
    if not sid or not tid:
        return None
    return os.path.join(SNAPSHOT_DIR, re.sub(r"[^\w.-]", "_", "%s-%s" % (sid, tid)))


def take_snapshot(data, extensions):
    path = (data.get("tool_input") or {}).get("file_path") or ""
    target = snapshot_path(data)
    if not target or not path.lower().endswith(tuple(extensions)):
        return
    try:
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        now = time.time()
        for old in glob.glob(os.path.join(SNAPSHOT_DIR, "*")):
            if now - os.path.getmtime(old) > SNAPSHOT_MAX_AGE:
                os.remove(old)
        if os.path.isfile(path):
            with open(path, "rb") as src, open(target, "wb") as dst:
                dst.write(src.read())
        else:
            open(target, "wb").close()           # a new file: everything in it is new
    except OSError:
        pass                                     # no snapshot: the report falls back to the committed version


def pop_snapshot(data):
    target = snapshot_path(data)
    if not target or not os.path.isfile(target):
        return None
    try:
        with open(target, "rb") as f:
            old = f.read()
        os.remove(target)
        return old
    except OSError:
        return None


# --- baseline from Git ---
def head_version(path):
    folder, name = os.path.dirname(path) or ".", os.path.basename(path)
    old = git(["cat-file", "--filters", "HEAD:./" + name], folder)    # as checked out: eol rules applied
    if not old:
        old = git(["show", "HEAD:./" + name], folder)                 # empty for a new file
    if LF in old and CR not in old:
        old = old.replace(b"\n", b"\r\n")        # stored as LF, nothing converts it: the working copy is meant to be CRLF
    return old


def changed_files(data, cwd, extensions):
    tool = data.get("tool_name")
    inp = data.get("tool_input") or {}
    if tool in ("Write", "Edit"):
        path = inp.get("file_path") or ""
        return [path] if path.lower().endswith(tuple(extensions)) else []
    if tool not in ("Bash", "PowerShell"):
        return []
    top = git_root(cwd)
    specs = [":(top,icase)*" + e for e in extensions]
    out = git(["status", "--porcelain", "-z", "--"] + specs, top)
    now, result = time.time(), []
    entries = out.decode("utf-8", "replace").split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        if entry[0] in "RC":
            i += 1                               # rename / copy: the next entry is the old path
        if entry[0] == "D" or entry[1] == "D":
            continue
        path = os.path.join(top, entry[3:])
        try:
            if now - os.path.getmtime(path) <= WINDOW_SEC:
                result.append(path)
        except OSError:
            pass
    return result


def is_binary_dfm(head):
    # same rule as tools/dfm_text_check.py (hooks do not import from tools/)
    return head.startswith(b"TPF0") or (head[:1] == b"\xff" and b"TPF0" in head[:512])


def check(path, s, old=None):
    try:
        data = open(path, "rb").read()
    except OSError:
        return []
    name = os.path.basename(path)
    if path.lower().endswith(".dfm") and is_binary_dfm(data[:512]):
        return ["%s is a binary DFM: it cannot be read or edited as text. Do not change it; ask the developer to convert it "
                "to text (IDE: right-click the form > Text DFM, save; or Delphi's bin\\convert.exe -i -t). "
                "tools/dfm_text_check.py lists all binary DFMs." % name]
    if old is None:
        old = head_version(path)
    problems = []
    if bare_lf(data) > bare_lf(old):
        problems.append("%s: %d lines end with a bare LF (%d before); line endings must be CRLF"
                        % (name, bare_lf(data), bare_lf(old)))
    if s["source_encoding"].lower().replace("-", "") not in ("utf8", "utf8sig") and is_utf8(data) and not is_utf8(old):
        problems.append("%s: file was saved as UTF-8; sources must be %s" % (name, s["source_encoding"]))
    for fp in s["forbidden_patterns"]:
        try:
            pat = re.compile(fp["pattern"].encode("utf-8"), re.I)
        except (re.error, KeyError, TypeError, AttributeError) as e:
            problems.append("forbidden_patterns entry %r in the settings is not a valid pattern (%s); fix it" % (fp, e))
            continue
        new_n, old_n = len(pat.findall(data)), len(pat.findall(old))
        if new_n > old_n:
            problems.append("%s: %s (%d -> %d)" % (name, fp.get("message", fp["pattern"]), old_n, new_n))
    lines = double_signature(data, s)
    if lines:
        problems.append("%s: two consecutive comment lines both end with today's signature (line %s); the signature "
                        "belongs on the last line of the explanation only" % (name, ", ".join(str(n) for n in lines[:5])))
    return problems


def main():
    try:
        data = hook_common.read_input()
    except ValueError as e:
        print(json.dumps({"decision": "block", "reason": "Pascal file check could not read the hook input (%s); the "
                          "changed files were not checked." % e}))
        return 0
    s, settings_problem = hook_common.load_settings(DEFAULTS)
    extensions = [e.lower() for e in s["pascal_extensions"]]
    if data.get("hook_event_name") == "PreToolUse":
        take_snapshot(data, extensions)
        return 0
    cwd = data.get("cwd") or hook_common.project_root()
    problems = [settings_problem] if settings_problem else []
    snapshot = pop_snapshot(data) if data.get("tool_name") in ("Write", "Edit") else None
    for path in changed_files(data, cwd, extensions):
        problems.extend(check(path, s, snapshot))
    if problems:
        print(json.dumps({
            "decision": "block",
            "reason": "Pascal file check - fix before continuing:\n- " + "\n- ".join(problems)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
