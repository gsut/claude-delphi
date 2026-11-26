"""Summary of build.bat output: errors and warnings / hints that are NEW compared with the baseline.

In a legacy project with thousands of warnings "no warnings" is meaningless; the criterion is "0 errors and 0 new warnings
compared with the baseline".

Language independent: a localized Delphi or MSBuild writes "warning", "Warnung", "avertissement", "uyari" ... in its own
language, so the kind is taken from the message code, never from the word: E / F = error, W = warning, H = hint
(Delphi compiler), and MSBuild's MSBnnnn codes.

Comparison key (file, code, message); the line number is not part of the key because edits shift lines. If a key occurs
more often than in the baseline, the surplus counts as new.
Usage: summary.py <log> <baseline> <msbuild_exit_code> [baseline]
"""
import re
import sys
from collections import Counter

# "<file>(<line>): <localized kind words> <code>: <message> [<project>]"
DELPHI = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+)\):\s.*?\b(?P<code>[EFWH]\d{4}):\s(?P<msg>.*?)(?:\s\[[^\]]*\])?$"
)
# MSBuild / tool errors: "... error MSB1009: ..." ; the MSBuild canonical format keeps the "error" keyword, but match the code
MSBUILD = re.compile(r"\b(?:error|fatal)\b.*?\b[A-Z]{2,}\d{3,}\s*:|\bMSB\d{4}\s*:", re.I)
MSBUILD_WARNING = re.compile(r"\bwarning\b.*?\b[A-Z]{2,}\d{3,}\s*:", re.I)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return [s.rstrip("\r\n") for s in f]


def main():
    log, baseline, rc = sys.argv[1], sys.argv[2], int(sys.argv[3])
    save_baseline = len(sys.argv) > 4 and sys.argv[4].lower() == "baseline"
    lines = read(log)

    errors, warnings = [], []
    for s in lines:
        m = DELPHI.match(s.strip())
        if m:
            (errors if m["code"][0] in "EF" else warnings).append(m)
        elif MSBUILD.search(s) and not MSBUILD_WARNING.search(s):
            errors.append(s.strip())

    key = lambda m: f'{m["file"].lower()}\t{m["code"]}\t{m["msg"]}'
    now = Counter(key(m) for m in warnings)
    w = sum(1 for m in warnings if m["code"][0] == "W")
    print(f"msbuild exit code: {rc}  errors: {len(errors)}  warnings: {w}  hints: {len(warnings) - w}")

    for e in errors[:50]:
        print("ERROR:", e if isinstance(e, str) else f'{e["file"]}({e["line"]}) {e["code"]}: {e["msg"]}')

    if save_baseline:
        with open(baseline, "w", encoding="utf-8") as f:
            for k, n in sorted(now.items()):
                f.write(f"{n}\t{k}\n")
        print(f"baseline saved: {len(now)} distinct warning keys")
        return

    try:
        old = Counter()
        for s in read(baseline):
            n, k = s.split("\t", 1)
            old[k] = int(n)
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
