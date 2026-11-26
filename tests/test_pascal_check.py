import datetime
import os
import unittest

from helpers import BINARY_DFM, TEXT_DFM, TempProject, run_hook

SETTINGS = {
    "source_encoding": "cp1254",
    "signature_pattern": "[A-Z]{2,4} - {date}",
    "date_format": "%Y-%m-%d",
    "forbidden_patterns": [{"pattern": r"BoolToStr\s*\([^)\r\n]*,\s*True\s*\)", "message": "BoolToStr(x, True) added"}],
}


class PascalCheckTest(unittest.TestCase):
    def setUp(self):
        self.project = TempProject(SETTINGS, git=True)
        self.path = os.path.join(self.project.dir, "Unit1.pas")

    def tearDown(self):
        self.project.close()

    def check(self, data):
        with open(self.path, "wb") as f:
            f.write(data)
        out = run_hook("pascal_check.py", {"tool_name": "Write", "tool_input": {"file_path": self.path},
                                           "cwd": self.project.dir}, self.project)
        return (out or {}).get("reason", "")

    def test_clean_file_is_silent(self):
        self.assertEqual(self.check("unit Unit1;\r\n// Ölçüm\r\nend.\r\n".encode("cp1254")), "")

    def test_reports_each_violation(self):
        today = datetime.date.today().strftime("%Y-%m-%d")
        text = ("unit Unit1;\r\n// Ölçüm\r\n// first AB - %s\r\n// second AB - %s\r\n"
                "s := BoolToStr(b, True);\nend.\r\n" % (today, today))
        reason = self.check(text.encode("utf-8"))
        self.assertIn("bare LF", reason)
        self.assertIn("UTF-8", reason)
        self.assertIn("BoolToStr", reason)
        self.assertIn("signature", reason)

    def test_signature_on_last_line_only_is_fine(self):
        today = datetime.date.today().strftime("%Y-%m-%d")
        text = "unit Unit1;\r\n// why it changed\r\n// more reasoning. AB - %s\r\nend.\r\n" % today
        self.assertEqual(self.check(text.encode("cp1254")), "")

    def test_binary_dfm_reported(self):
        path = os.path.join(self.project.dir, "Form1.dfm")
        with open(path, "wb") as f:
            f.write(BINARY_DFM)
        out = run_hook("pascal_check.py", {"tool_name": "Write", "tool_input": {"file_path": path},
                                           "cwd": self.project.dir}, self.project)
        self.assertIn("binary DFM", (out or {}).get("reason", ""))

    def test_text_dfm_is_silent(self):
        path = os.path.join(self.project.dir, "Form2.dfm")
        with open(path, "wb") as f:
            f.write(TEXT_DFM)
        out = run_hook("pascal_check.py", {"tool_name": "Write", "tool_input": {"file_path": path},
                                           "cwd": self.project.dir}, self.project)
        self.assertIsNone(out)

    def test_non_pascal_files_ignored(self):
        path = os.path.join(self.project.dir, "notes.txt")
        with open(path, "wb") as f:
            f.write("ü\n".encode("utf-8"))
        out = run_hook("pascal_check.py", {"tool_name": "Write", "tool_input": {"file_path": path}}, self.project)
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main()
