import os
import shutil
import tempfile
import unittest

from helpers import BINARY_DFM, TOOLS, run_tool, write_sample

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


UNIT = (
    "unit U;\ninterface\ntype\n  TForm1 = class(TForm)\n"
    "    procedure WMSize(var M: TMessage); message WM_SIZE;\n"
    "    procedure CreateParams(var P: TCreateParams); override;\n"
    "    procedure Run;\n  end;\n"
    "procedure Helper;\nprocedure UpdateUI;\n"
    "implementation\n"
    "procedure Helper;\nbegin\nend;\n"
    "procedure UpdateUI;\nbegin\nend;\n"
    "procedure TForm1.WMSize(var M: TMessage);\nbegin\n  inherited;\nend;\n"
    "procedure TForm1.CreateParams(var P: TCreateParams);\nbegin\n  inherited;\nend;\n"
    "procedure TForm1.Run;\nbegin\n  TThread.Synchronize(nil, procedure begin UpdateUI; end);\nend;\n"
    "end.\n"
)


class PasCallersVerdictTest(unittest.TestCase):
    """The dead-code verdict must not be given when something speaks against it (found by an independent review: each of
    these used to print "no reference ... Evidence for a dead-code marker")."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="claude-delphi-test-")
        write_sample(self.dir, "U.pas", UNIT)
        write_sample(self.dir, "Project.dpr", "program Project;\nuses\n  U in 'U.pas';\nbegin\nend.\n")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def callers(self, name, root=None):
        r = run_tool(PAS_CALLERS, ["--root", root or self.dir, name])
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_call_inside_parameterless_anonymous_method(self):
        self.assertIn("verdict: referenced", self.callers("UpdateUI"))

    def test_framework_methods_get_no_verdict(self):
        for name in ("WMSize", "CreateParams"):
            with self.subTest(name=name):
                out = self.callers(name)
                self.assertIn("NO VERDICT", out)
                self.assertIn("called by the framework", out)
                self.assertNotIn("Evidence for a dead-code marker", out)

    def test_reference_from_unit_not_in_dpr(self):
        os.makedirs(os.path.join(self.dir, "lib"))
        write_sample(self.dir, os.path.join("lib", "Report.pas"),
                     "unit Report;\ninterface\nimplementation\nuses U;\nprocedure Print;\nbegin\n  Helper;\nend;\nend.\n")
        out = self.callers("Helper")
        self.assertIn("NO VERDICT", out)
        self.assertIn("units the .dpr does not list", out)

    def test_binary_dfm_is_not_searched_silently(self):
        with open(os.path.join(self.dir, "U.dfm"), "wb") as f:
            f.write(BINARY_DFM)
        out = self.callers("Helper")
        self.assertIn("binary DFM", out)
        self.assertIn("NO VERDICT", out)

    def test_exported_routine(self):
        write_sample(self.dir, "Project.dpr", "library Project;\nuses\n  U in 'U.pas';\nexports Helper;\nbegin\nend.\n")
        out = self.callers("Helper")
        self.assertIn("exported (called from outside): 1", out)
        self.assertNotIn("Evidence for a dead-code marker", out)    # the exports line itself counts as a reference

    def test_dpr_unit_outside_root(self):
        app = os.path.join(self.dir, "app")
        os.makedirs(app)
        write_sample(app, "Project.dpr",
                     "program Project;\nuses\n  U in '..\\U.pas',\n  Main in 'Main.pas';\nbegin\nend.\n")
        write_sample(app, "Main.pas", "unit Main;\ninterface\nprocedure Lonely;\nimplementation\n"
                                      "procedure Lonely;\nbegin\nend;\nend.\n")
        out = self.callers("Lonely", root=app)
        self.assertIn("outside --root", out)
        self.assertIn("NO VERDICT", out)

    def test_plain_unused_routine_still_gets_the_verdict(self):
        out = self.callers("Run")
        self.assertIn("Evidence for a dead-code marker", out)


if __name__ == "__main__":
    unittest.main()
