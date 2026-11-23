import os
import shutil
import tempfile
import unittest

from helpers import TOOLS, run_tool, write_sample

PAS_CALLERS = os.path.join(TOOLS, "pas_callers.py")

OTHER = (
    "unit Other;\n"
    "interface\n"
    "procedure Unused;\n"
    "implementation\n"
    "procedure Unused;\n"
    "begin\n"
    "  Unused; // recursion only\n"
    "  F := Owner.FindComponent('Inner');\n"
    "end;\n"
    "end.\n"
)
DPR = "program Project;\nuses\n  Sample in 'Sample.pas';\nbegin\nend.\n"
DFM = "object Form1: TForm1\r\n  object Button1: TButton\r\n    OnClick = Second\r\n  end\r\nend\r\n"


class PasCallersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="claude-delphi-test-")
        write_sample(cls.dir)
        write_sample(cls.dir, "Other.pas", OTHER)
        write_sample(cls.dir, "Project.dpr", DPR)
        with open(os.path.join(cls.dir, "Form1.dfm"), "w", encoding="ascii", newline="") as f:
            f.write(DFM)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def callers(self, name):
        r = run_tool(PAS_CALLERS, ["--root", self.dir, name])
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_nested_routine_call(self):
        out = self.callers("Inner")
        self.assertIn("definitions: 1", out)
        self.assertIn("TForm1.First > Inner", out)
        self.assertIn("in TForm1.First  Inner", out)
        self.assertIn("name strings: 1", out)                      # FindComponent('Inner') in Other.pas
        self.assertIn("Other.pas [not in .dpr]", out)
        self.assertIn("verdict: referenced", out)

    def test_dfm_binding(self):
        out = self.callers("Second")
        self.assertIn("DFM bindings: 1", out)
        self.assertIn("OnClick = Second", out)
        self.assertIn("verdict: referenced", out)

    def test_recursion_and_comments_only_is_dead(self):
        out = self.callers("Unused")
        self.assertIn("self", out)
        self.assertIn("verdict: no reference outside its own body", out)

    def test_declarations_are_not_calls(self):
        out = self.callers("First")      # declared in the class, defined, and called from Second
        self.assertIn("code references: 1", out)
        self.assertIn("in TForm1.Second  First", out)


if __name__ == "__main__":
    unittest.main()
