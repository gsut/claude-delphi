import datetime
import json
import os
import subprocess
import unittest

from helpers import BINARY_DFM, ROOT, TEXT_DFM, TempProject, run_hook

CRLF_UNIT = b"unit Unit1;\r\ninterface\r\nconst a;\r\nimplementation\r\nconst a;\r\nend.\r\n"


def git(project, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "core.autocrlf=false", *args],
                   cwd=project.dir, check=True, capture_output=True)

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

    # --- baseline: the committed version as checked out, or the snapshot taken before the tool ran ---
    def commit(self, data, attributes=None):
        if attributes is not None:
            with open(os.path.join(self.project.dir, ".gitattributes"), "w", encoding="utf-8") as f:
                f.write(attributes)
        with open(self.path, "wb") as f:
            f.write(data)
        git(self.project, "add", ".")
        git(self.project, "commit", "-q", "-m", "base")

    def test_repository_storing_lf_with_eol_attribute(self):
        # the .gitattributes of the installation guide stores LF: `git show` gives a blob without CR, and new bare LFs
        # used to go unreported
        with open(os.path.join(ROOT, "examples", "gitattributes"), encoding="utf-8") as f:
            self.commit(CRLF_UNIT, f.read())
        self.assertIn("2 lines end with a bare LF (0 before)", self.check(CRLF_UNIT.replace(b"a;\r\n", b"a;\n")))
        self.assertEqual(self.check(CRLF_UNIT), "")

    def test_repository_storing_lf_without_conversion(self):
        # LF in the repository, nothing converts it, the working copy is CRLF (seen in a real project)
        self.commit(CRLF_UNIT.replace(b"\r\n", b"\n"))
        with open(self.path, "wb") as f:
            f.write(CRLF_UNIT)
        self.assertEqual(self.check(CRLF_UNIT), "")
        self.assertIn("bare LF", self.check(CRLF_UNIT.replace(b"a;\r\n", b"a;\n")))

    def test_snapshot_before_edit_is_the_baseline(self):
        # a file that already has bare LFs: an edit that keeps them is silent, one more is reported
        legacy = b"unit Unit1;\ninterface\nimplementation\r\nend.\r\n"
        self.commit(CRLF_UNIT)                             # the committed version says nothing about this state
        with open(self.path, "wb") as f:
            f.write(legacy)
        ids = {"session_id": "s1", "tool_use_id": "t1", "cwd": self.project.dir}
        pre = dict(ids, hook_event_name="PreToolUse", tool_name="Edit", tool_input={"file_path": self.path})
        self.assertIsNone(run_hook("pascal_check.py", pre, self.project))
        post = dict(pre, hook_event_name="PostToolUse")
        with open(self.path, "wb") as f:
            f.write(legacy.replace(b"end.\r\n", b"// x\r\nend.\r\n"))
        self.assertIsNone(run_hook("pascal_check.py", post, self.project))
        ids["tool_use_id"] = "t2"
        pre = dict(ids, hook_event_name="PreToolUse", tool_name="Edit", tool_input={"file_path": self.path})
        run_hook("pascal_check.py", pre, self.project)
        with open(self.path, "wb") as f:
            f.write(legacy.replace(b"end.\r\n", b"// x\nend.\r\n"))
        out = run_hook("pascal_check.py", dict(pre, hook_event_name="PostToolUse"), self.project)
        self.assertIn("3 lines end with a bare LF (2 before)", out["reason"])

    def test_non_ascii_path(self):
        folder = os.path.join(self.project.dir, "Gökhan")
        os.makedirs(folder)
        self.path = os.path.join(folder, "Müşteri.pas")
        self.assertIn("bare LF", self.check(b"unit A;\nend.\r\n"))

    def test_bash_finds_files_anywhere_in_any_case(self):
        self.commit(CRLF_UNIT)
        for rel in ("src/UNIT2.PAS", "other/Unit3.pas"):
            p = os.path.join(self.project.dir, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(b"unit A;\nend.\n")
        cwd = os.path.join(self.project.dir, "other")       # a sibling folder of src/
        out = run_hook("pascal_check.py", {"tool_name": "Bash", "tool_input": {"command": "x"}, "cwd": cwd},
                       self.project)
        self.assertIn("UNIT2.PAS", out["reason"])
        self.assertIn("Unit3.pas", out["reason"])

    def test_invalid_pattern_is_reported_and_other_checks_still_run(self):
        p = TempProject(dict(SETTINGS, forbidden_patterns=[{"pattern": "BoolToStr(", "message": "x"}]), git=True)
        try:
            self.project, self.path = p, os.path.join(p.dir, "Unit1.pas")
            reason = self.check(b"unit A;\nend.\r\n")
            self.assertIn("not a valid pattern", reason)
            self.assertIn("bare LF", reason)
        finally:
            p.close()

    def test_settings_with_bom_are_used_and_broken_ones_reported(self):
        conf = os.path.join(self.project.dir, ".claude", "claude-delphi.json")
        with open(conf, "wb") as f:
            f.write(b"\xef\xbb\xbf" + json.dumps(SETTINGS).encode("utf-8"))
        self.assertIn("BoolToStr", self.check(b"unit A;\r\ns := BoolToStr(b, True);\r\nend.\r\n"))
        with open(conf, "w", encoding="utf-8") as f:
            f.write('{"source_encoding": "cp1254",}')
        self.assertIn("cannot be read", self.check(CRLF_UNIT))

    def test_unreadable_input_is_reported(self):
        out = run_hook("pascal_check.py", None, self.project, raw=b"not json")
        self.assertIn("could not read the hook input", out["reason"])

    def test_non_pascal_files_ignored(self):
        path = os.path.join(self.project.dir, "notes.txt")
        with open(path, "wb") as f:
            f.write("ü\n".encode("utf-8"))
        out = run_hook("pascal_check.py", {"tool_name": "Write", "tool_input": {"file_path": path}}, self.project)
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main()
