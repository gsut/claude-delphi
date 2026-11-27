"""Change map: maps every hunk of a Git diff to the routine (Pascal) or object chain (DFM) it belongs to. Read only.

The close-out audit (/close-out step 2b, agent `closeout-auditor`) takes this output as input: it is the mechanical part of
"was anything touched outside the plan?". Judgement (was the touch needed, did something break) stays with the agent and
the developer.

Usage:  python tools/diff_routines.py [--rev A..B | --commit X] [--plan <plan.md>] [-- <path> ...]
  (default)     working tree + staged changes against HEAD; untracked new files are listed separately
  --rev A..B    between two revisions;  --commit X  one commit (X^..X)
  --plan        plan file: for each routine / object, whether its name occurs in the plan ("NOT IN PLAN" = review it).
                If the plan uses the template's section markers (.claude/templates/plan.md), only the sections
                plan:items and plan:scope are searched; a name in the evidence or in "other callers" does not count.

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


# Git settings of the machine must not change the result: an external diff tool (diff.external / GIT_EXTERNAL_DIFF) or a
# textconv driver would replace the patch and every change would look like "no hunks"; diff.interHunkContext would merge
# hunks and charge untouched lines in between.
DIFF_OPTIONS = ["--no-ext-diff", "--no-textconv", "--ignore-cr-at-eol", "-U0", "--inter-hunk-context=0", "--no-color"]


def diff_raw(span, path):
    """the -U0 patch of one file (bytes)"""
    return git("diff", "--relative", *DIFF_OPTIONS, *span, "--", path, raw=True)


def no_hunk_reason(span, path):
    """why a changed file has no hunk: binary, new and empty, or line endings only"""
    num = git("diff", "--relative", "--no-ext-diff", "--no-textconv", "--ignore-cr-at-eol", "--numstat", *span,
              "--", path).strip()
    if num.startswith("-\t-"):
        return "binary content changed (not mapped)"
    status = git("diff", "--relative", "--no-ext-diff", "--name-status", *span, "--", path).strip()
    if status.startswith("A"):
        return "new empty file"
    return "line endings only (CRLF / LF); content unchanged"


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


PLAN_MARKER = re.compile(r"^\s*<!--\s*plan:([\w-]+)\s*-->\s*$")
PLAN_SECTIONS = ("items", "scope")


FILE_EXTENSIONS = {".pas", ".dfm", ".dpr", ".dproj", ".dpk", ".inc", ".md", ".sql", ".txt", ".json", ".py", ".bat",
                   ".xml", ".rc", ".res", ".ini", ".cfg"}
NAME = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")


def plan_sections(text):
    """{section: text} from the <!-- plan:... --> markers; {} if the plan has none"""
    sections, current = {}, None
    for line in text.split("\n"):
        m = PLAN_MARKER.match(line)
        if m:
            current = m.group(1).lower()
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)
    return {k: "\n".join(v) for k, v in sections.items()}


def plan_text(text):
    """(searched text, note): the plan:items and plan:scope sections if the plan has section markers, else all of it."""
    sections = plan_sections(text)
    if not sections:
        return text, "no section markers: the whole plan is searched"
    found = [s for s in PLAN_SECTIONS if s in sections]
    if not found:
        return "", "section markers but no plan:items / plan:scope section: nothing counts as in plan"
    return "\n".join(sections[s] for s in found), "searched sections: " + ", ".join(found)


def scope_names(scope):
    """(files, names) written in `backticks` in the plan's Scope section; other backticked text (code) is skipped"""
    files, names = [], []
    for tok in re.findall(r"`([^`\n]+)`", scope):
        tok = tok.strip()
        if os.path.splitext(tok)[1].lower() in FILE_EXTENSIONS:
            files.append(tok)
        elif NAME.fullmatch(tok):
            names.append(tok)
    return files, names


def not_changed(files, names, changed_files, changed_names):
    """the Scope entries that no change touches"""
    paths = [p.replace("\\", "/").lower() for p in changed_files]
    missing = []
    for f in files:
        t = f.replace("\\", "/").lower().lstrip("./")
        if not any(p == t or p.endswith("/" + t) for p in paths):
            missing.append(f)
    for n in names:
        t = n.lower()
        # a class counts as changed when one of its methods changed (a method added to the class declaration is mapped to
        # unit level, not to the class)
        if not any(c == t or c.endswith("." + t) or ("." not in t and c.startswith(t + ".")) for c in changed_names):
            missing.append(n)
    return missing


def comment_or_blank(line):
    s = line.strip()
    return not s or s.startswith(("//", "{", "(*", "}", "*)"))


DECLARATION = re.compile(r"^\s*(?:class\s+)?(?:procedure|function|constructor|destructor|operator)\s+([\w.]+)", re.I)


def declared_after(lines, last):
    """name declared by the first code line after line `last` (1-based) — a routine header in the implementation or a
    declaration in the interface / a class; None if that line is something else"""
    for s in lines[last:]:
        if comment_or_blank(s):
            continue
        m = DECLARATION.match(s)
        return m.group(1) if m else None
    return None


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
    """(label, short name, next routine): the next routine only for a line at unit level"""
    r = routine_at(rs, line)
    if r:
        return r.path(), r.short, None
    n = next_routine(rs, line)
    if n:
        return "(unit level; next routine %s, line %d)" % (n.path(), n.line), None, n
    return "(unit level)", None, None


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
        return "(?)", None, None
    path = omap[line] or "(start of file)"
    return path, path.split(" > ")[-1] if omap[line] else None, None


def routine_names(r):
    """every name a Scope entry may use for a routine: each level's name (TForm1.First, Inner) and its short name"""
    out = set()
    while r:
        out.update((r.name.lower(), r.short.lower()))
        r = r.parent
    return out


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

    plan = plan_note = scope = None
    if a.plan:
        with open(a.plan, encoding="utf-8") as f:
            raw_plan = f.read()
        plan, plan_note = plan_text(raw_plan)
        plan = plan.lower()
        scope = plan_sections(raw_plan).get("scope")
    changed_names = set()

    def in_plan(short, cls=None):
        # whole word: a short name ("Load") must not count when it is part of a longer word in the plan ("Loader"); and
        # a mention qualified with another class ("TFormA.Button1Click") does not cover TFormB.Button1Click. cls None =
        # the class is unknown (a DFM object, a declaration inside a class): any mention counts.
        for m in re.finditer(r"(?<![\w])" + re.escape(short.lower()) + r"(?![\w])", plan):
            q = re.search(r"(\w+)\.$", plan[:m.start()])
            if q and cls is not None and q.group(1) != cls.lower():
                continue
            return True
        return False

    def class_of(name):
        last = name.split(" > ")[-1]
        return last.rsplit(".", 1)[0] if "." in last else ""

    limit = ["--"] + (a.paths or ["."])
    files = [x for x in git("diff", "--relative", "--no-ext-diff", "--name-only", *span, *limit).split("\n")
             if x.strip()]
    print("Change map: %s" % ("working tree against HEAD" if new_rev is None else "%s..%s" % (old_rev, new_rev)))
    if plan is not None:
        print("Plan: %s (%s)" % (a.plan, plan_note))
    print()

    not_in_plan = []
    for path in files:
        raw = diff_raw(span, path)
        hs = hunks(raw.decode(encoding_of(path), "replace"))
        if not hs:
            print("## %s\n  %s\n" % (path, no_hunk_reason(span, path)))
            continue
        print("## %s  (+%d / -%d, %d hunks)" % (path, sum(len(h[5]) for h in hs), sum(len(h[4]) for h in hs), len(hs)))
        low = path.lower()
        new_lines = None
        if low.endswith(PASCAL):
            new_text = content(new_rev, path)
            new_lines = new_text.split("\n") if new_text is not None else None
            old_rs, old_note = routine_map(content(old_rev, path))
            new_rs, new_note = routine_map(new_text)
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

        def run(place, start, count, field, prefix, shown, texts):
            prev = None
            for i in range(count):
                label, short, nxt = place(start + i)
                key = (label, short)
                grp = groups.setdefault(key, {"+": 0, "-": 0, "lines": [], "code": False, "comment": False, "last": 0})
                grp[field] += 1
                if field == "+":
                    grp["last"] = max(grp["last"], start + i)
                # line by line, not per hunk: a comment added together with the routine below it is one hunk
                if i < len(texts):
                    if not comment_or_blank(texts[i]):
                        grp["code"] = True
                    elif texts[i].strip():
                        grp["comment"] = True
                if key != prev:
                    grp["lines"].append("%s%d%s" % (prefix, start + i, " [%s]" % shown if shown else ""))
                prev = key

        for h in hs:
            note = kind(h[4], h[5])
            run(new_place, h[2], h[3], "+", "", note, h[5])
            run(old_place, h[0], h[1], "-", "o", note if not h[3] else "", h[4])
        for (name, short), grp in groups.items():
            status = ""
            changed_names.update(x.strip().lower() for x in name.split(" > "))
            if short:
                changed_names.add(short.lower())
            # added comment lines at unit level belong to what the next code line declares: a routine header (a dead-code
            # marker, the explanation of a new routine) or a declaration in the interface / a class. Followed by anything
            # else they belong to nothing; blank lines alone are spacing. Neither gets a plan status.
            above = None
            if not short and grp["comment"] and not grp["code"] and grp["last"] and new_lines is not None:
                above = declared_after(new_lines, grp["last"])
            if above:
                changed_names.update((above.lower(), above.split(".")[-1].lower()))
            check = short or (above.split(".")[-1] if above else None)
            if short:
                cls = None if low.endswith(DFM) else class_of(name)
            else:                                # a declaration inside a class does not name its class
                cls = above.rsplit(".", 1)[0] if above and "." in above else None
            if plan is not None and check:
                if in_plan(check, cls):
                    status = "  in plan" if short else "  in plan (comment above %s)" % check
                else:
                    status = "  NOT IN PLAN"
                    not_in_plan.append("%s: %s" % (path, name))
            print("  %s  (+%d / -%d; lines %s)%s" % (name, grp["+"], grp["-"], ", ".join(grp["lines"]), status))
        print()

    new = []
    if new_rev is None:
        new = [x for x in git("ls-files", "--others", "--exclude-standard", *limit).split("\n") if x.strip()]
        if new:
            # Claude cannot `git add`, so every unit it creates is here: its routines are new and checked like the others
            print("## Untracked new files")
            for x in new:
                print("  " + x)
                if not x.lower().endswith(PASCAL):
                    continue
                rs, note = routine_map(content(None, x))
                if note:
                    print("    WARNING: %s" % note)
                for r in rs or []:
                    changed_names.update(routine_names(r))
                    status = ""
                    if plan is not None:
                        if in_plan(r.short, class_of(r.path())):
                            status = "  in plan"
                        else:
                            status = "  NOT IN PLAN"
                            not_in_plan.append("%s: %s" % (x, r.path()))
                    print("    %s  (new, line %d)%s" % (r.path(), r.line, status))
            print()

    if plan is not None:
        print("Routines / objects whose name is not in the plan: %d" % len(not_in_plan))
        for x in not_in_plan:
            print("  " + x)
    if scope is not None:
        # the other direction: Scope lists only what will change, so an entry nothing touches is a forgotten item, a
        # contingency that belongs in plan:contingency, or a step still to come (e.g. a document updated at close-out)
        missing = not_changed(*scope_names(scope), files + new, changed_names)
        print("\nNamed in the plan's Scope (`backticked`) but not changed: %d" % len(missing))
        for x in missing:
            print("  " + x)
    if not files:
        print("No changes.")


if __name__ == "__main__":
    main()
