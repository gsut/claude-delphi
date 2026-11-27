"""Close-out checks: the mechanical part of /close-out step 2 and the /build-check notes, in one command. Read only.

Each check prints OK, FAIL, NOTE or SKIP. The exit code is 1 if any check FAILs, else 0. NOTE lines need no fix; they go
into the report for the developer (/close-out section 5).

  measure-marker   no line with the measure marker (`measure_marker`, default X-MEASURE) in a Pascal / DFM file
  backup-files     no untracked .bak of a source file (Unit1.pas.bak, Unit1.bak, notes.md.bak; ignored ones included; one
                   that predates the job is listed too). Build products such as Project.exe.bak are not reported.
  createform       no added `CreateForm` line in a .dpr
  new-form         every new unit with a DFM is registered: unit and {FormName} in a .dpr, <Form>FormName</Form> in
                   a .dproj (a unit that belongs to a package is reported too; say so in the report)
  build-log        the build log (`build_log`, default build/log/last.log) is newer than every changed Pascal / DFM /
                   project file, i.e. /build-check ran after the last change. Its result is read by /build-check, not here.
  data-module      NOTE: a changed unit declares a TDataModule -> "close and reopen the project in Delphi"
  review-log       with --plan only (else SKIP): the review log next to the plan (<id>-plan.md -> <id>-reviews.md,
                   template .claude/templates/reviews.md) exists, every row is well formed, and it has a close-out row
                   dated today (written in /close-out step 2b)

What needs judgement stays with the session: whether each fix comment says why it changed, the "what the old call also
did" table. A comment signature on two lines in a row is reported by hooks/pascal_check.py when the file is written.

Usage:  python tools/closeout_check.py [--base REV] [--plan PLAN]
  --base REV   compare the working tree with REV (default HEAD); use the commit before the job if it is already committed
  --plan PLAN  the approved plan file; enables the review-log check

The project root and settings are found as in diff_routines.py ($CLAUDE_PROJECT_DIR, else the nearest folder upwards
holding .claude/claude-delphi.json, else the current folder).
"""
import argparse
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # find diff_routines / pascal_lex when run with -I too
import diff_routines as dr  # noqa: E402

MARKER = dr.CONF.get("measure_marker", "X-MEASURE")
BUILD_LOG = dr.CONF.get("build_log", "build/log/last.log")
SOURCES = tuple(x.lower() for x in dr.CONF.get("pascal_extensions", [".pas", ".dfm", ".dpr", ".inc"]))
BUILD_INPUTS = SOURCES + (".dfm", ".dpr", ".dproj", ".dpk")
BACKUP_SOURCES = set(BUILD_INPUTS) | {x.lower() for x in dr.CONF.get(
    "protected_extensions", [".pas", ".dfm", ".dpr", ".dproj", ".inc", ".py", ".md"])}
DATA_MODULE = re.compile(r"=\s*class\s*\(\s*TDataModule\s*\)", re.I)
DFM_ROOT = re.compile(r"^\s*(?:object|inherited|inline)\s+(\w+)\s*:", re.I)
SHOW = 20                                       # lines listed per check
REVIEW_COLUMNS = ["Date", "Step", "Round", "Agent", "Findings", "Accepted", "Accepted critical", "Not opened", "Note"]
REVIEW_STEPS = {"review", "multi-review", "close-out", "after-close-out"}
COUNTS = slice(4, 8)                            # Findings, Accepted, Accepted critical, Not opened


def lines_of(text):
    return [x for x in text.split("\n") if x.strip()]


def read(path):
    with open(os.path.join(dr.ROOT, path), "rb") as f:
        return f.read().decode(dr.encoding_of(path), "replace").replace("\r\n", "\n")


def exists(path):
    return os.path.isfile(os.path.join(dr.ROOT, path))


class Files:
    def __init__(self, base):
        g = dr.git
        self.untracked = lines_of(g("ls-files", "--others", "--exclude-standard"))
        self.changed = [x for x in lines_of(g("diff", "--relative", "--name-only", base, "--", ".")) if exists(x)]
        self.changed += self.untracked
        self.added = lines_of(g("diff", "--relative", "--name-only", "--diff-filter=A", base, "--", ".")) + self.untracked
        self.sources = [x for x in lines_of(g("ls-files", "--cached", "--others", "--exclude-standard"))
                        if x.lower().endswith(SOURCES + (".dfm",)) and exists(x)]
        self.all_untracked = lines_of(g("ls-files", "--others"))      # ignored files too


def check_marker(f, base):
    hits = []
    for path in f.sources:
        for i, line in enumerate(read(path).split("\n"), 1):
            if MARKER in line:
                hits.append("%s:%d  %s" % (path, i, line.strip()))
    if hits:
        return "FAIL", "%d line(s) with \"%s\" left" % (len(hits), MARKER), hits
    return "OK", "no \"%s\" line in %d Pascal / DFM files" % (MARKER, len(f.sources)), []


def source_backup(path):
    """a .bak of a source / text file (Unit1.pas.bak, notes.md.bak) or without a second extension (Unit1.bak);
    not a build product such as Project.exe.bak, which an exe packer (e.g. ASPack) writes on every build"""
    if not path.lower().endswith(".bak"):
        return False
    stem_ext = os.path.splitext(os.path.basename(path)[:-4])[1].lower()
    return not stem_ext or stem_ext in BACKUP_SOURCES


def check_backup(f, base):
    found = [x for x in f.all_untracked if source_backup(x)]
    if found:
        return "FAIL", "%d untracked .bak file(s) of source files; delete the ones this job created" % len(found), found
    return "OK", "no untracked .bak file of a source file", []


def check_createform(f, base):
    hits = []
    for path in [x for x in f.changed if x.lower().endswith(".dpr")]:
        if path in f.untracked:
            continue                                            # a new project: its CreateForm lines are not "added"
        raw = dr.diff_raw([base], path)
        for h in dr.hunks(raw.decode(dr.encoding_of(path), "replace")):
            for i, line in enumerate(h[5]):
                if "createform" in line.lower():
                    hits.append("%s:%d  %s" % (path, h[2] + i, line.strip()))
    if hits:
        return "FAIL", "%d added CreateForm line(s) in .dpr" % len(hits), hits
    return "OK", "no added CreateForm line in .dpr", []


def check_new_form(f, base):
    dprs = [read(x).lower() for x in f.sources if x.lower().endswith(".dpr")]
    dprojs = [read(x).lower() for x in lines_of(dr.git("ls-files", "--cached", "--others", "--exclude-standard"))
              if x.lower().endswith(".dproj") and exists(x)]
    problems, checked = [], 0
    for pas in [x for x in f.added if x.lower().endswith(".pas")]:
        dfm = pas[:-4] + ".dfm"
        if not exists(dfm):
            continue
        m = next((DFM_ROOT.match(x) for x in read(dfm).split("\n") if x.strip()), None)
        if not m:
            problems.append("%s: cannot read the form name from the first line" % dfm)
            continue
        checked += 1
        unit, form = os.path.splitext(os.path.basename(pas))[0].lower(), m.group(1).lower()
        missing = []
        if not any(re.search(r"\b%s\s+in\s+'" % re.escape(unit), d) for d in dprs):
            missing.append("unit in .dpr uses")
        # {Form1}, and for a data module / frame {DmMain: TDataModule} / {Frame1: TFrame}
        if not any(re.search(r"\{\s*%s\s*(?::[^}]*)?\}" % re.escape(form), d) for d in dprs):
            missing.append("{%s} in .dpr" % m.group(1))
        if not any("<form>%s</form>" % form in d for d in dprojs):
            missing.append("<Form>%s</Form> in .dproj" % m.group(1))
        if missing:
            problems.append("%s: missing %s" % (pas, ", ".join(missing)))
    if not dprs and checked:
        return "FAIL", "new form unit(s) but no .dpr found in the project", problems
    if problems:
        return "FAIL", "%d new form unit(s) not registered (a package unit: say so in the report)" % len(problems), problems
    return "OK", "%d new form unit(s), all registered" % checked if checked else "no new form unit", []


def check_build_log(f, base):
    inputs = [x for x in f.changed if x.lower().endswith(BUILD_INPUTS)]
    if not inputs:
        return "OK", "no Pascal / DFM / project file changed", []
    log = os.path.join(dr.ROOT, BUILD_LOG)
    if not os.path.isfile(log):
        return "FAIL", "no build log (%s): run /build-check" % BUILD_LOG, []
    built = os.path.getmtime(log)
    newer = [x for x in inputs if os.path.getmtime(os.path.join(dr.ROOT, x)) > built]
    if newer:
        return "FAIL", "%d file(s) changed after the last build: run /build-check" % len(newer), newer
    return "OK", "build log is newer than all %d changed file(s)" % len(inputs), []


def check_data_module(f, base):
    found = [x for x in f.changed if x.lower().endswith(".pas") and DATA_MODULE.search(read(x))]
    if found:
        return "NOTE", "data module changed: tell the developer to close and reopen the project in Delphi", found
    return "OK", "no data module changed", []


def review_log_path(plan):
    folder, name = os.path.split(os.path.abspath(plan))
    stem = name[:-len("-plan.md")] if name.lower().endswith("-plan.md") else os.path.splitext(name)[0]
    return os.path.join(folder, stem + "-reviews.md")


def table_cells(line):
    """cells of a Markdown table row; "\\|" inside a cell is a literal bar"""
    parts = re.split(r"(?<!\\)\|", line.strip())
    return [p.strip().replace("\\|", "|") for p in parts[1:-1]]


def review_rows(text):
    """(rows, problems): rows as lists of cells, header and separator skipped; problems describe malformed rows"""
    rows, problems, header = [], [], None
    for n, line in enumerate(text.split("\n"), 1):
        if not line.strip().startswith("|"):
            continue
        cells = table_cells(line)
        if header is None:
            header = cells
            if header != REVIEW_COLUMNS:
                problems.append("line %d: header is not | %s |" % (n, " | ".join(REVIEW_COLUMNS)))
            continue
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        why = []
        if len(cells) != len(REVIEW_COLUMNS):
            why.append("%d cells instead of %d (a | inside a cell is written \\|)" % (len(cells), len(REVIEW_COLUMNS)))
        else:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
                why.append("date is not YYYY-MM-DD")
            if cells[1] not in REVIEW_STEPS:
                why.append("step is not one of %s" % ", ".join(sorted(REVIEW_STEPS)))
            counts = cells[COUNTS]
            if not all(c.isdigit() for c in counts):
                why.append("Findings / Accepted / Accepted critical / Not opened must be whole numbers")
            else:
                found, accepted, critical, unopened = map(int, counts)
                if accepted > found or unopened > found:
                    why.append("Accepted and Not opened cannot exceed Findings")
                if critical > accepted:
                    why.append("Accepted critical cannot exceed Accepted")
        if why:
            problems.append("line %d: %s" % (n, "; ".join(why)))
        else:
            rows.append(cells)
    if header is None:
        problems.append("no table")
    return rows, problems


def check_review_log(f, base):
    if not f.plan:
        return "SKIP", "no --plan given", []
    log = review_log_path(f.plan)
    if not os.path.isfile(log):
        return "FAIL", "no review log: %s (template .claude/templates/reviews.md)" % log, []
    with open(log, encoding="utf-8") as fh:
        rows, problems = review_rows(fh.read())
    today = datetime.date.today().isoformat()
    if not any(r[1] == "close-out" and r[0] == today for r in rows):
        problems.append("no close-out row dated %s (/close-out step 2b)" % today)
    if problems:
        return "FAIL", "review log %s: %d problem(s)" % (os.path.basename(log), len(problems)), problems
    return "OK", "review log %s: %d row(s), close-out recorded today" % (os.path.basename(log), len(rows)), []


CHECKS = [("measure-marker", check_marker), ("backup-files", check_backup), ("createform", check_createform),
          ("new-form", check_new_form), ("build-log", check_build_log), ("data-module", check_data_module),
          ("review-log", check_review_log)]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Mechanical close-out checks (read only).")
    p.add_argument("--base", default="HEAD")
    p.add_argument("--plan")
    a = p.parse_args()

    f = Files(a.base)
    f.plan = a.plan
    print("Close-out checks: working tree against %s\n" % a.base)
    fails = 0
    for name, check in CHECKS:
        status, text, details = check(f, a.base)
        fails += status == "FAIL"
        print("%-5s %-15s %s" % (status, name, text))
        for d in details[:SHOW]:
            print("        " + d)
        if len(details) > SHOW:
            print("        ... %d more" % (len(details) - SHOW))
    print("\nResult: %s" % ("%d FAIL" % fails if fails else "no FAIL"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
