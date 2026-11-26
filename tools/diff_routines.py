"""Change map: maps every hunk of a Git diff to the routine (Pascal) or object chain (DFM) it belongs to. Read only.

The close-out audit (/close-out step 2b, agent `closeout-auditor`) takes this output as input: it is the mechanical part of
"was anything touched outside the plan?". Judgement (was the touch needed, did something break) stays with the agent and
the developer.

Usage:  python tools/diff_routines.py [--rev A..B | --commit X] [--plan <plan.md>] [-- <path> ...]
  (default)     working tree + staged changes against HEAD; untracked new files are listed separately
  --rev A..B    between two revisions;  --commit X  one commit (X^..X)
  --plan        plan file: for each routine / object, whether its name occurs in the plan ("NOT IN PLAN" = review it)

The project root is $CLAUDE_PROJECT_DIR, else the nearest folder upwards holding .claude/claude-delphi.json, else the current
folder. Pascal / DFM files are read in `source_encoding` from
.claude/claude-delphi.json (default cp1252). Line-ending differences are ignored (--ignore-cr-at-eol: many Delphi repositories
store LF and check out CRLF). A hunk that only changes whitespace, or only touches // comment lines, is marked.
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # find pascal_lex when run with -I too
import pascal_lex  # noqa: E402

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


ROOT = project_root()
DFM = (".dfm",)
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
OBJECT = re.compile(r"^\s*(object|inherited|inline)\s+([\w]+)?\s*:?\s*([\w.]+)?", re.I)


def settings():
    try:
        with open(os.path.join(ROOT, ".claude", "claude-delphi.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


CONF = settings()
ENCODING = CONF.get("source_encoding", "cp1252")
PASCAL = tuple(x.lower() for x in CONF.get("pascal_extensions", [".pas", ".dfm", ".dpr", ".inc"])
               if x.lower() not in DFM) + (".dpk",)


def git(*args, raw=False):
    # core.quotepath=off: a file name with non-ASCII letters would otherwise come back quoted / escaped and the diff for it
    # would be empty.
    r = subprocess.run(["git", "-C", ROOT, "-c", "core.quotepath=off", *args], capture_output=True)
    if r.returncode != 0:
        sys.exit("git %s: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout if raw else r.stdout.decode("utf-8", "replace")


def encoding_of(path):
    return ENCODING if path.lower().endswith(PASCAL + DFM) else "utf-8"


def content(rev, path):
    """rev None = the file on disk; None if the file does not exist in that revision."""
    if rev is None:
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            return None
        with open(full, "rb") as f:
            data = f.read()
    else:
        r = subprocess.run(["git", "-C", ROOT, "show", "%s:./%s" % (rev, path)], capture_output=True)
        if r.returncode != 0:
            return None
        data = r.stdout
    return data.decode(encoding_of(path), "replace").replace("\r\n", "\n")


def hunks(diff_text):
    """[(old_start, old_count, new_start, new_count, [-lines], [+lines])]"""
    result, cur = [], None
    for line in diff_text.split("\n"):
        m = HUNK.match(line)
        if m:
            cur = [int(m.group(1)), int(m.group(2) or 1), int(m.group(3)), int(m.group(4) or 1), [], []]
            result.append(cur)
        elif cur is not None and line.startswith("-") and not line.startswith("---"):
            cur[4].append(line[1:].rstrip("\r"))
        elif cur is not None and line.startswith("+") and not line.startswith("+++"):
            cur[5].append(line[1:].rstrip("\r"))
    return result


def kind(minus, plus):
    if sorted(re.sub(r"\s+", "", x) for x in minus) == sorted(re.sub(r"\s+", "", x) for x in plus):
        return "whitespace only"
    lines = [x.strip() for x in minus + plus if x.strip()]
    if lines and all(x.startswith("//") for x in lines):
        return "// comment only"
    return ""


# --- Pascal: line -> innermost routine ---
def routine_map(text):
    if text is None:
        return None, "no file"
    try:
        return pascal_lex.routines(text), ""
    except pascal_lex.ParseError as e:
        return None, "could not parse: %s" % e


def routine_at(rs, line):
    best = None
    for r in rs or []:
        if r.end_line is not None and r.line <= line <= r.end_line and (best is None or r.line >= best.line):
            best = r
    return best


def next_routine(rs, line):
    cands = [r for r in rs or [] if r.line > line and r.parent is None]
    return min(cands, key=lambda r: r.line) if cands else None


def pascal_place(rs, line):
    r = routine_at(rs, line)
    if r:
        return r.path(), r.short
    n = next_routine(rs, line)
    if n:
        return "(unit level; next routine %s, line %d)" % (n.path(), n.line), None
    return "(unit level)", None


# --- DFM: line -> object chain ---
def object_map(text):
    """for every line, the chain of objects containing it (Form > Panel > Button)"""
    if text is None:
        return None
    # Collection items (item ... end / end>) also close with "end"; they enter the stack nameless (None) and are not shown.
    stack, result = [], [""]
    chain = lambda: " > ".join(x for x in stack if x)  # noqa: E731
    for line in text.split("\n"):
        s = line.strip().lower()
        m = OBJECT.match(line)
        if m and m.group(2):
            stack.append(m.group(2))
            result.append(chain())
        elif s == "item":
            stack.append(None)
            result.append(chain())
        elif s in ("end", "end>") and stack:
            result.append(chain())
            stack.pop()
        else:
            result.append(chain())
    return result


def dfm_place(omap, line):
    if not omap or line >= len(omap):
        return "(?)", None
    path = omap[line] or "(start of file)"
    return path, path.split(" > ")[-1] if omap[line] else None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Map diff hunks to routines / DFM objects (read only).")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--rev")
    g.add_argument("--commit")
    p.add_argument("--plan")
    p.add_argument("paths", nargs="*")
    a = p.parse_args()

    if a.commit:
        old_rev, new_rev, span = a.commit + "^", a.commit, [a.commit + "^", a.commit]
    elif a.rev:
        if ".." not in a.rev:
            sys.exit("--rev must be A..B")
        old_rev, new_rev = a.rev.split("..", 1)
        span = [old_rev, new_rev]
    else:
        old_rev, new_rev, span = "HEAD", None, ["HEAD"]

    plan = None
    if a.plan:
        with open(a.plan, encoding="utf-8") as f:
            plan = f.read().lower()

    limit = ["--"] + (a.paths or ["."])
    files = [x for x in git("diff", "--relative", "--name-only", *span, *limit).split("\n") if x.strip()]
    print("Change map: %s" % ("working tree against HEAD" if new_rev is None else "%s..%s" % (old_rev, new_rev)))
    if plan is not None:
        print("Plan: %s" % a.plan)
    print()

    not_in_plan = []
    for path in files:
        raw = git("diff", "--relative", "--ignore-cr-at-eol", "-U0", "--no-color", *span, "--", path, raw=True)
        hs = hunks(raw.decode(encoding_of(path), "replace"))
        if not hs:
            print("## %s\n  line endings only (CRLF / LF); content unchanged\n" % path)
            continue
        print("## %s  (+%d / -%d, %d hunks)" % (path, sum(len(h[5]) for h in hs), sum(len(h[4]) for h in hs), len(hs)))
        low = path.lower()
        if low.endswith(PASCAL):
            old_rs, old_note = routine_map(content(old_rev, path))
            new_rs, new_note = routine_map(content(new_rev, path))
            for n in (old_note, new_note):
                if n and n != "no file":
                    print("  WARNING: %s" % n)
            new_place = lambda s: pascal_place(new_rs, s)  # noqa: E731
            old_place = lambda s: pascal_place(old_rs, s)  # noqa: E731
        elif low.endswith(DFM):
            old_m, new_m = object_map(content(old_rev, path)), object_map(content(new_rev, path))
            new_place = lambda s: dfm_place(new_m, s)  # noqa: E731
            old_place = lambda s: dfm_place(old_m, s)  # noqa: E731
        else:
            new_place = None

        if new_place is None:
            for h in hs:
                start = h[2] if h[3] else h[0]
                print("  line %d: +%d / -%d" % (start, len(h[5]), len(h[4])))
            print()
            continue

        # Line by line: one hunk can span several routines / objects (new routines added one after another would all be
        # charged to the first). Added lines are looked up in the new file, removed lines in the old one; the line list
        # holds the first line of each continuous run (old-file lines carry the prefix "o").
        groups = {}

        def run(place, start, count, field, prefix, note):
            prev = None
            for i in range(count):
                key = place(start + i)
                grp = groups.setdefault(key, {"+": 0, "-": 0, "lines": []})
                grp[field] += 1
                if key != prev:
                    grp["lines"].append("%s%d%s" % (prefix, start + i, " [%s]" % note if note else ""))
                prev = key

        for h in hs:
            note = kind(h[4], h[5])
            run(new_place, h[2], h[3], "+", "", note)
            run(old_place, h[0], h[1], "-", "o", note if not h[3] else "")
        for (name, short), grp in groups.items():
            status = ""
            if plan is not None and short:
                # whole word: a short name ("Load") must not count when it is part of a longer word in the plan ("Loader")
                if re.search(r"(?<![\w])" + re.escape(short.lower()) + r"(?![\w])", plan):
                    status = "  in plan"
                else:
                    status = "  NOT IN PLAN"
                    not_in_plan.append("%s: %s" % (path, name))
            print("  %s  (+%d / -%d; lines %s)%s" % (name, grp["+"], grp["-"], ", ".join(grp["lines"]), status))
        print()

    if new_rev is None:
        new = [x for x in git("ls-files", "--others", "--exclude-standard", *limit).split("\n") if x.strip()]
        if new:
            print("## Untracked new files")
            for x in new:
                print("  " + x)
            print()

    if plan is not None:
        print("Routines / objects whose name is not in the plan: %d" % len(not_in_plan))
        for x in not_in_plan:
            print("  " + x)
    if not files:
        print("No changes.")


if __name__ == "__main__":
    main()
