"""Safe text replacement in Pascal / DFM files that keeps the code page and CRLF line endings.

The hooks forbid sed -i and shell redirection on Pascal files; this is the tool to use instead.

Usage:   python pas_edit.py <edits.json> [--dry-run] [--reverse]
         --reverse undoes a spec that was applied: every "new" becomes the anchor and is replaced by its "old", last edit
         first (additions_only is ignored). Handy for removing temporary measurement lines with the spec that added them.
edits.json:
  {
    "file": "Source/Main.pas",
    "encoding": "cp1252",            optional; default: source_encoding from .claude/claude-delphi.json, else cp1252
    "additions_only": false,         optional; true = refuse if any existing line would be removed or changed
    "edits": [
      {"old": "  Result := X;\\n", "new": "  // why it changed. AB - 2026-01-31\\n  Result := Y;\\n",
       "routine": "TMainForm.Button1Click"}       optional; search only inside this routine ("Outer > Inner" for nested)
    ]
  }
Write "old" / "new" with \\n line breaks; they are converted to the file's CRLF.

Rules (nothing is written if any rule fails):
- every "old" must occur exactly once (inside the routine when "routine" is given); edits apply in order;
- an "old" that ends with a line break matches only at the start of a line (never inside a more indented line);
- "routine" must match exactly one routine; for copies of the same routine in one file, give the routine;
- the new text must be representable in the file's code page; text inserted into a DFM must be ASCII (#nnn escapes for others);
- with additions_only, the line diff must contain no removed lines.
Prints a unified diff of the change. Exit code 0 on success, 1 on refusal.
"""
import argparse
import difflib
import json
import os
import sys

sys.dont_write_bytecode = True   # no __pycache__ next to the tools in the user's project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pascal_lex  # noqa: E402
from dfm_text_check import HOW, is_binary_dfm  # noqa: E402

# the diff contains source text (any code page); print it as UTF-8, not in the console's code page
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def project_root():
    """$CLAUDE_PROJECT_DIR, else the nearest folder upwards holding .claude/claude-delphi.json, else the current folder."""
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        return os.environ["CLAUDE_PROJECT_DIR"]
    d = os.getcwd()
    while True:
        if os.path.isfile(os.path.join(d, ".claude", "claude-delphi.json")):
            return d
        up = os.path.dirname(d)
        if up == d:
            return os.getcwd()
        d = up


def project_encoding():
    root = project_root()
    try:
        with open(os.path.join(root, ".claude", "claude-delphi.json"), encoding="utf-8") as f:
            return json.load(f).get("source_encoding", "cp1252")
    except (OSError, ValueError):
        return "cp1252"


def refuse(msg):
    print("REFUSED: " + msg)
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverse", action="store_true")
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    if a.reverse:
        spec["edits"] = [dict(ed, old=ed["new"], new=ed["old"]) for ed in reversed(spec["edits"])]
        spec.pop("additions_only", None)
    path = spec["file"]
    is_dfm = path.lower().endswith(".dfm")
    enc = spec.get("encoding") or project_encoding()
    raw = open(path, "rb").read()
    if is_dfm and is_binary_dfm(raw[:512]):
        refuse("%s is a binary DFM; it cannot be edited as text. Ask the developer to %s "
               "(tools/dfm_text_check.py lists all of them)" % (path, HOW))
    if raw.startswith(b"\xef\xbb\xbf"):
        enc = "utf-8-sig"
    try:
        text = raw.decode(enc)
    except UnicodeDecodeError as e:
        refuse("%s does not decode as %s (%s); set 'encoding'" % (path, enc, e))
    crlf = b"\r\n" in raw
    nl = "\r\n" if crlf else "\n"
    original = text

    for n, ed in enumerate(spec["edits"], 1):
        old = ed["old"].replace("\r\n", "\n").replace("\n", nl)
        new = ed["new"].replace("\r\n", "\n").replace("\n", nl)
        if not old:
            refuse("edit %d: 'old' is empty" % n)
        lo, hi = 0, len(text)
        if ed.get("routine"):
            if is_dfm:
                refuse("edit %d: 'routine' is for Pascal files" % n)
            try:
                found = pascal_lex.find_routine(pascal_lex.routines(text), ed["routine"])
            except pascal_lex.ParseError as e:
                refuse("edit %d: cannot parse %s: %s" % (n, path, e))
            # a forward / external declaration has no body to edit: only routines with a body count
            with_body = [r for r in found if r.body_start is not None]
            found = with_body if with_body else found
            if len(found) != 1:
                where = ", ".join("%s (line %d)" % (r.path(), r.line) for r in found) or "none"
                refuse("edit %d: routine '%s' matches %d routines: %s" % (n, ed["routine"], len(found), where))
            lo, hi = found[0].start, found[0].end
            # the routine ends at the ';' of its final "end;" -- include the line break, so a whole-line anchor
            # that ends with that "end;" still falls inside the routine
            if text.startswith(nl, hi):
                hi += len(nl)
        # an anchor written as whole lines (ending with a line break) matches only at the start of a line, so that
        # "  X;\n" does not match inside "    X;\n" of a deeper block and split that line
        whole_lines = old.endswith(nl)
        hits, k = [], text.find(old, lo, hi)
        while k >= 0:
            if not whole_lines or k == 0 or text[k - 1] == "\n":
                hits.append(k)
            k = text.find(old, k + 1, hi)
        if len(hits) != 1:
            scope = "routine '%s'" % ed["routine"] if ed.get("routine") else "the file"
            refuse("edit %d: 'old' occurs %d times in %s (must be exactly once)" % (n, len(hits), scope))
        k = hits[0]
        text = text[:k] + new + text[k + len(old):]

    # only the inserted text is checked: some IDE-saved DFMs (UTF-8 with BOM) already contain non-ASCII characters
    if is_dfm and any(ord(c) > 127 for ed in spec["edits"] for c in ed["new"]):
        refuse("new DFM text must be ASCII; write non-ASCII characters as #nnn escapes")
    try:
        out = text.encode(enc)
    except UnicodeEncodeError as e:
        refuse("new text is not representable in %s: %r" % (enc, text[e.start:e.end]))

    old_lines, new_lines = original.splitlines(), text.splitlines()
    diff = list(difflib.unified_diff(old_lines, new_lines, path, path, lineterm="", n=2))
    if spec.get("additions_only"):
        # exact test (a diff may show a pure insertion as -/+ when the same line occurs twice): every original line
        # must still be there, in the same order
        it = iter(new_lines)
        missing = [ln for ln in old_lines if not any(ln == x for x in it)]
        if missing:
            refuse("additions_only is set but existing line(s) would change or disappear:\n%s" % "\n".join(missing[:10]))
    removed = len(old_lines) + sum(1 for d in diff if d.startswith("+") and not d.startswith("+++")) - len(new_lines)
    print("\n".join(diff) if diff else "(no change)")
    if a.dry_run:
        print("dry run: nothing written")
        return
    with open(path, "wb") as f:
        f.write(out)
    added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    print("written: %s (%s, %s), +%d -%d lines" % (path, enc, "CRLF" if crlf else "LF", added, removed))


if __name__ == "__main__":
    main()
