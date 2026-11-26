# Claude Code PostToolUse (Write | Edit | Bash) hook: mechanical rules for Pascal / DFM files that were just changed.
#   1. Line endings: CRLF only (no newly added bare LF).
#   2. Encoding: if sources use a single-byte ANSI code page (cp1252, cp1254, cp1251 ...), a file saved as UTF-8 is an error.
#   3. Project-specific forbidden patterns ("forbidden_patterns" in the settings; e.g. BoolToStr(x, True)).
#   4. If a signature pattern is set: two consecutive comment lines must not both end with today's signature
#      (the signature belongs on the last line of an explanation only).
#   5. A binary DFM among the changed files is reported (it cannot be read or edited as text; ask the developer to convert it).
# Only NEW violations are reported: counts are compared with the file's committed (HEAD) version, so existing legacy code
# does not create noise. The hook never touches the file; it only reports (PostToolUse "block" = feedback to Claude).
# Settings: $CLAUDE_PROJECT_DIR/.claude/claude-delphi.json (defaults below if missing).
import datetime
import json
import os
import re
import subprocess
import sys
import time

DEFAULTS = {
    "pascal_extensions": [".pas", ".dfm", ".dpr", ".inc"],
    "source_encoding": "cp1252",
    "forbidden_patterns": [],        # [{"pattern": "<regex>", "message": "..."}]
    "signature_pattern": "",         # e.g. "[A-Z]{2,4} - {date}"; {date} = today in date_format
    "date_format": "%d.%m.%Y",
}
WINDOW_SEC = 600                     # after Bash: files changed in the last 10 minutes
CR, LF = 13, 10


def settings():
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    s = dict(DEFAULTS)
    try:
        with open(os.path.join(root, ".claude", "claude-delphi.json"), encoding="utf-8") as f:
            s.update(json.load(f))
    except (OSError, ValueError):
        pass
    return s


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


def changed_files(data, root, extensions):
    tool = data.get("tool_name")
    inp = data.get("tool_input") or {}
    if tool in ("Write", "Edit"):
        path = inp.get("file_path") or ""
        return [path] if path.lower().endswith(tuple(extensions)) else []
    if tool != "Bash":
        return []
    out = git(["status", "--porcelain", "-z", "--"] + ["*" + e for e in extensions], root)
    now, result = time.time(), []
    for entry in out.decode("utf-8", "replace").split("\0"):
        if len(entry) < 4 or entry[0] == "D" or entry[1] == "D":
            continue
        path = os.path.join(git_root(root), entry[3:])
        try:
            if now - os.path.getmtime(path) <= WINDOW_SEC:
                result.append(path)
        except OSError:
            pass
    return result


def head_version(path):
    folder = os.path.dirname(path) or "."
    return git(["show", "HEAD:./" + os.path.basename(path)], folder)   # empty for a new file


def is_binary_dfm(head):
    # same rule as tools/dfm_text_check.py (hooks do not import from tools/)
    return head.startswith(b"TPF0") or (head[:1] == b"\xff" and b"TPF0" in head[:512])


def check(path, s):
    try:
        data = open(path, "rb").read()
    except OSError:
        return []
    name = os.path.basename(path)
    if path.lower().endswith(".dfm") and is_binary_dfm(data[:512]):
        return ["%s is a binary DFM: it cannot be read or edited as text. Do not change it; ask the developer to convert it "
                "to text (IDE: right-click the form > Text DFM, save; or Delphi's bin\\convert.exe -i -t). "
                "tools/dfm_text_check.py lists all binary DFMs." % name]
    old = head_version(path)
    problems = []
    if bare_lf(data) > bare_lf(old):
        problems.append("%s: %d lines end with a bare LF (%d in the committed version); line endings must be CRLF"
                        % (name, bare_lf(data), bare_lf(old)))
    if s["source_encoding"].lower().replace("-", "") not in ("utf8", "utf8sig") and is_utf8(data) and not is_utf8(old):
        problems.append("%s: file was saved as UTF-8; sources must be %s" % (name, s["source_encoding"]))
    for fp in s["forbidden_patterns"]:
        pat = re.compile(fp["pattern"].encode("utf-8"), re.I)
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
        data = json.load(sys.stdin)
    except Exception:
        return 0
    s = settings()
    root = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    problems = []
    for path in changed_files(data, root, [e.lower() for e in s["pascal_extensions"]]):
        problems.extend(check(path, s))
    if problems:
        print(json.dumps({
            "decision": "block",
            "reason": "Pascal file check - fix before continuing:\n- " + "\n- ".join(problems)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
