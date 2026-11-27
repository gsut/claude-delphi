import os
import tempfile
import unittest

from helpers import BUILD, run_tool

SUMMARY = os.path.join(BUILD, "summary.py")
P = " [C:\\p\\Project.dproj]"


def write(folder, name, lines):
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")
    return path


class SummaryTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="claude-delphi-test-")
        self.baseline = os.path.join(self.dir, "baseline.txt")

    def run_summary(self, log, rc=0, *extra):
        return run_tool(SUMMARY, [log, self.baseline, str(rc)] + list(extra)).stdout

    def test_localized_messages_are_classified_by_code(self):
        log = write(self.dir, "loc.log", [
            "Unit1.pas(10): warning W1036: Variable 'x' might not have been initialized" + P,
            "Unit1.pas(11): Warnung W1036: Variable 'y' ist moeglicherweise nicht initialisiert" + P,
            "Unit1.pas(12): Hinweis H2164: Variable 'z' wurde deklariert, aber nie verwendet" + P,
            "Unit3.pas(7): avertissement W1000: Symbole 'A' est deprecie" + P,
            "Unit2.pas(5): Fehler E2003: Undeklarierter Bezeichner: 'q'" + P,
            "Lib.pas(51): warning W1000: Symbol 'RaiseLastWin32Error' is deprecated" + P,
            "MSBUILD : error MSB1009: Proje dosyasi yok.",
        ])
        out = self.run_summary(log, 1)
        self.assertIn("errors: 2  warnings: 4  hints: 1", out)

    def test_new_warning_detected_and_line_shift_ignored(self):
        base = write(self.dir, "base.log", [
            "Unit1.pas(10): warning W1036: Variable 'x' might not have been initialized" + P,
            "Unit1.pas(20): Hint warning H2164: Variable 'y' is declared but never used" + P,
        ])
        out = self.run_summary(base, 0, "baseline")
        self.assertIn("baseline saved", out)
        now = write(self.dir, "now.log", [
            "Unit1.pas(14): warning W1036: Variable 'x' might not have been initialized" + P,   # shifted, not new
            "Unit1.pas(24): Hint warning H2164: Variable 'y' is declared but never used" + P,   # shifted, not new
            "Unit1.pas(30): warning W1035: Return value of function 'F' might be undefined" + P,  # new
        ])
        out = self.run_summary(now)
        self.assertIn("new warnings/hints vs baseline: 1", out)
        self.assertIn("NEW: Unit1.pas(30) W1035", out)

    def test_removed_warning_reported(self):
        base = write(self.dir, "base.log", ["Unit1.pas(10): warning W1036: Variable 'x' might not be set" + P])
        self.run_summary(base, 0, "baseline")
        now = write(self.dir, "now.log", ["Build succeeded."])
        out = self.run_summary(now)
        self.assertIn("new warnings/hints vs baseline: 0", out)
        self.assertIn("in baseline but no longer present: 1", out)

    # --- a failed build must never read as "0 errors" (found by an independent reliability review) ---
    def test_line_and_column_format(self):
        log = write(self.dir, "f.log", [
            "C:\\x\\CodeGear.Delphi.Targets(396,5): error F1026: File not found: 'Project.dpr'" + P])
        self.assertIn("errors: 1", self.run_summary(log, 1))

    def test_failed_build_without_a_known_error_line(self):
        for line in ("'msbuild' is not recognized as an internal or external command,",
                     "C:\\x\\Targets(10,5): Fehler MSB4018: Die Aufgabe ist unerwartet fehlgeschlagen."):
            with self.subTest(line=line):
                out = self.run_summary(write(self.dir, "x.log", [line]), 9009)
                self.assertIn("errors: 1", out)
                self.assertIn("build failed (msbuild exit code 9009)", out)

    def test_localized_msbuild_warning_is_not_an_error(self):
        log = write(self.dir, "w.log", ["Proje.dproj : Warnung MSB4011: x wird nicht importiert", "Build succeeded."])
        self.assertIn("errors: 0", self.run_summary(log, 0))

    def test_no_baseline_from_a_failed_build(self):
        log = write(self.dir, "f.log", ["Unit2.pas(5): error E2003: Undeclared identifier: 'q'" + P])
        out = self.run_summary(log, 1, "baseline")
        self.assertIn("baseline NOT saved", out)
        self.assertFalse(os.path.exists(self.baseline))

    def test_blank_line_in_baseline_and_non_ascii_message(self):
        base = write(self.dir, "base.log", ["Unit1.pas(10): warning W1036: Değişken 'x' ilk değer almamış" + P])
        self.run_summary(base, 0, "baseline")
        with open(self.baseline, "a", encoding="utf-8") as f:
            f.write("\n\n")
        now = write(self.dir, "now.log", ["Ünite.pas(3): warning W1036: Değişken 'ş' ilk değer almamış" + P])
        out = self.run_summary(now)
        self.assertIn("new warnings/hints vs baseline: 1", out)

    def test_missing_baseline(self):
        log = write(self.dir, "x.log", ["Build succeeded."])
        self.assertIn("no baseline", self.run_summary(log))


if __name__ == "__main__":
    unittest.main()
