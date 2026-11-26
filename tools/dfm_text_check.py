"""Finds binary DFM files in a project. Read only.

Claude, the hooks and the tools in this package can only read and edit text DFMs; a binary DFM (very old projects, or
"Text DFM" switched off in the IDE) is unreadable for them, and a `text` rule in .gitattributes would corrupt it. Convert
binary DFMs to text before working with Claude, and before adding .gitattributes.

Usage:  python tools/dfm_text_check.py [--root <project folder>]     (default: the current folder)
Exit code 1 if any binary DFM was found, else 0.

How to convert (the developer does this; the tool never changes a file):
  - in the IDE: open the form, right-click it > "Text DFM", save; or
  - Delphi's command-line converter in the bin folder: convert.exe -i -t <file.dfm>  (run convert.exe without arguments to
    check the options of your version).
"""
import argparse
import os
import sys

SKIP_DIRS = {".git", ".svn", ".hg", "__history", "__recovery", "node_modules"}
HOW = ('convert them to text: open the form in the IDE, right-click > "Text DFM", save; or Delphi\'s bin\\convert.exe '
       '-i -t <file.dfm> (run convert.exe without arguments to check its options)')


def is_binary_dfm(head):
    """head: the first bytes of a .dfm. A binary DFM is a resource ("FF 0A 00" + name) holding a "TPF0" stream, or a bare
    "TPF0" stream. A text DFM starts with "object" / "inherited" / "inline" (possibly after a BOM and white space)."""
    if head.startswith(b"TPF0"):
        return True
    return head[:1] == b"\xff" and b"TPF0" in head[:512]


def read_head(path, size=512):
    try:
        with open(path, "rb") as f:
            return f.read(size)
    except OSError:
        return b""


def binary_dfms(root):
    found = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.lower().endswith(".dfm"):
                path = os.path.join(folder, name)
                if is_binary_dfm(read_head(path)):
                    found.append(os.path.relpath(path, root))
    return sorted(found)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="List binary DFM files (read only).")
    ap.add_argument("--root", default=os.getcwd())
    a = ap.parse_args()
    found = binary_dfms(a.root)
    if not found:
        print("No binary DFM found.")
        return 0
    print("%d binary DFM file(s); %s:" % (len(found), HOW))
    for p in found:
        print("  " + p)
    return 1


if __name__ == "__main__":
    sys.exit(main())
