"""Summary of build.bat output: errors and warnings / hints that are NEW compared with the baseline.

In a legacy project with thousands of warnings "no warnings" is meaningless; the criterion is "0 errors and 0 new warnings
compared with the baseline".

Language independent: a localized Delphi or MSBuild writes "warning", "Warnung", "avertissement", "uyari" ... in its own
language, so the kind is taken from the message code, never from the word: E / F = error, W = warning, H = hint
(Delphi compiler), and MSBuild's MSBnnnn codes.

Comparison key (file, code, message); the line number is not part of the key because edits shift lines. If a key occurs
more often than in the baseline, the surplus counts as new.

A failed build always shows as an error: if MSBuild exits with a non-zero code and no error line was recognised (a
message format this script does not know, a localized MSBuild error, msbuild not found), a generic error is counted.
A baseline is saved only from a build without errors.
Usage: summary.py <log> <baseline> <msbuild_exit_code> [baseline]
"""
import re
import sys
from collections import Counter

# "<file>(<line>[,<column>]): <localized kind words> <code>: <message> [<project>]"
DELPHI = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+)(?:,\d+)?\):\s.*?\b(?P<code>[EFWH]\d{4}):\s(?P<msg>.*?)(?:\s\[[^\]]*\])?$"
)
# MSBuild / tool errors with the English keyword: "... error MSB1009: ...". A localized MSBuild writes the kind in its own
# language ("Warnung MSB4011", "Fehler MSB1009"); without the keyword the kind is unknown, so such a line is not counted
# here — a real failure still shows through the exit code.
MSBUILD_ERROR = re.compile(r"\b(?:error|fatal)\b\s*:?\s*[A-Z]+\d{3,}\s*:", re.I)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return [s.rstrip("\r\n") for s in f]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    log, baseline, rc = sys.argv[1], sys.argv[2], int(sys.argv[3])
    save_baseline = len(sys.argv) > 4 and sys.argv[4].lower() == "baseline"
    lines = read(log)

    errors, warnings = [], []
    for s in lines:
        m = DELPHI.match(s.strip())
        if m:
            (errors if m["code"][0] in "EF" else warnings).append(m)
        elif MSBUILD_ERROR.search(s):
            errors.append(s.strip())
    if rc != 0 and not errors:
        errors.append("build failed (msbuild exit code %d) but no error line was recognised; read %s" % (rc, log))

    key = lambda m: f'{m["file"].lower()}\t{m["code"]}\t{m["msg"]}'
    now = Counter(key(m) for m in warnings)
    w = sum(1 for m in warnings if m["code"][0] == "W")
    print(f"msbuild exit code: {rc}  errors: {len(errors)}  warnings: {w}  hints: {len(warnings) - w}")

    for e in errors[:50]:
        print("ERROR:", e if isinstance(e, str) else f'{e["file"]}({e["line"]}) {e["code"]}: {e["msg"]}')

    if save_baseline:
        if errors:
            print("baseline NOT saved: the build has errors (a failed build has no warnings to compare with)")
            return
        with open(baseline, "w", encoding="utf-8") as f:
            for k, n in sorted(now.items()):
                f.write(f"{n}\t{k}\n")
        print(f"baseline saved: {len(now)} distinct warning keys")
        return

    try:
        old = Counter()
        for s in read(baseline):
            n, tab, k = s.partition("\t")
            if tab and n.isdigit():
                old[k] = int(n)                 # blank or foreign lines are skipped
    except FileNotFoundError:
        print("no baseline: run 'build.bat baseline' first")
        return

    new = now - old
    print(f"new warnings/hints vs baseline: {sum(new.values())}")
    for m in warnings:
        k = key(m)
        if new[k] > 0:
            new[k] -= 1
            print(f'NEW: {m["file"]}({m["line"]}) {m["code"]}: {m["msg"]}')
    gone = old - now
    if gone:
        print(f"in baseline but no longer present: {sum(gone.values())}")


if __name__ == "__main__":
    main()
