# Claude Code SessionStart hook: one-time project checks at the start of a session. Today: binary DFM files.
# Claude, the hooks and the tools can only read and edit text DFMs, and a "text" rule in .gitattributes would corrupt a
# binary one. If the project has binary DFMs, a note is printed; Claude Code adds a SessionStart hook's plain stdout to
# Claude's context, so Claude tells the developer in its first answer. Nothing is printed when all DFMs are text.
# The hook never changes a file. Settings: $CLAUDE_PROJECT_DIR/.claude/claude-delphi.json ("warn_binary_dfm", default true).
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python -I leaves the script's folder off sys.path
import hook_common  # noqa: E402

DEFAULTS = {"warn_binary_dfm": True}
SKIP_DIRS = {".git", ".svn", ".hg", "__history", "__recovery", "node_modules"}
TIME_LIMIT_SEC = 20                  # a very large tree is cut short rather than delaying the session
SHOW = 10


def is_binary_dfm(head):
    # same rule as tools/dfm_text_check.py (hooks do not import from tools/)
    return head.startswith(b"TPF0") or (head[:1] == b"\xff" and b"TPF0" in head[:512])


def binary_dfms(root):
    found, start, complete = [], time.time(), True
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.lower().endswith(".dfm"):
                path = os.path.join(folder, name)
                try:
                    with open(path, "rb") as f:
                        head = f.read(512)
                except OSError:
                    continue
                if is_binary_dfm(head):
                    found.append(os.path.relpath(path, root))
        if time.time() - start > TIME_LIMIT_SEC:
            complete = False
            break
    return sorted(found), complete


def main():
    try:
        data = hook_common.read_input()
    except ValueError:
        data = {}
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    s, problem = hook_common.load_settings(DEFAULTS, root)
    if problem:
        print("claude-delphi session check: %s. Tell the developer in your first answer: the hooks refuse every shell "
              "command until it is fixed." % problem)
    if not s.get("warn_binary_dfm", True):
        return 0
    found, complete = binary_dfms(root)
    if not found:
        if not complete:
            print("claude-delphi session check: the binary DFM scan was cut short after %d s and found none so far; that "
                  "does not mean there are none. Run python tools/dfm_text_check.py once." % TIME_LIMIT_SEC)
        return 0
    lines = ["claude-delphi session check: the project has %d binary DFM file(s)%s. Tell the developer in your first answer, "
             "before any other work: binary DFMs cannot be read or edited as text by Claude or the tools, and a text "
             "rule in .gitattributes would corrupt them. Ask them to convert them to text (IDE: open the form, right-click "
             "> Text DFM, save; or Delphi's bin\\convert.exe -i -t <file.dfm>). Do not change these files yourself. "
             "Full list: python tools/dfm_text_check.py" % (len(found), "" if complete else " (scan cut short)")]
    lines += ["  " + p for p in found[:SHOW]]
    if len(found) > SHOW:
        lines.append("  ... and %d more" % (len(found) - SHOW))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
