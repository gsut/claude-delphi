import datetime
import os
import subprocess
import time
import unittest

from helpers import ROOT, TOOLS, TempProject, run_tool, write_sample

CLOSEOUT = os.path.join(TOOLS, "closeout_check.py")

DPR = (
    "program Project;\n"
    "\n"
    "uses\n"
    "  Forms,\n"
    "  Sample in 'Sample.pas';\n"
    "\n"
    "begin\n"
    "  Application.Initialize;\n"
    "  Application.Run;\n"
    "end.\n"
)
DPROJ = "<Project>\n  <ItemGroup>\n  </ItemGroup>\n</Project>\n"
FORM_PAS = "unit Form2;\n\ninterface\n\nimplementation\n\n{$R *.dfm}\n\nend.\n"
FORM_DFM = "object Form2: TForm2\n  Caption = 'Two'\nend\n"
DATA_MODULE_PAS = (
    "unit Data;\n\ninterface\n\ntype\n  TDM = class(TDataModule)\n  end;\n\nimplementation\n\nend.\n"
)


def git(project, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   cwd=project.dir, check=True, capture_output=True)


class CloseoutCheckTest(unittest.TestCase):
    def setUp(self):
        self.p = TempProject({"source_encoding": "cp1254", "measure_marker": "X-MEASURE"}, git=True)
        git(self.p, "config", "core.autocrlf", "false")
        write_sample(self.p.dir)
        write_sample(self.p.dir, "Project.dpr", DPR)
        write_sample(self.p.dir, "Project.dproj", DPROJ, encoding="utf-8")
        git(self.p, "add", ".")
        git(self.p, "commit", "-q", "-m", "base")

    def tearDown(self):
        self.p.close()

    def write(self, name, text, encoding="cp1254"):
        write_sample(self.p.dir, name, text, encoding=encoding)

    def append(self, name, text):
        path = os.path.join(self.p.dir, name)
        with open(path, "ab") as f:
            f.write(text.replace("\n", "\r\n").encode("cp1254"))

    def replace(self, name, old, new):
        path = os.path.join(self.p.dir, name)
        with open(path, "rb") as f:
            data = f.read().decode("cp1254")
        self.assertIn(old, data)
        with open(path, "wb") as f:
            f.write(data.replace(old, new, 1).encode("cp1254"))

    def build_log(self, after_changes=True):
        folder = os.path.join(self.p.dir, "build", "log")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "last.log")
        with open(path, "w", encoding="utf-8") as f:
            f.write("build\n")
        stamp = time.time() + (60 if after_changes else -60)
        os.utime(path, (stamp, stamp))

    def run_check(self, *args, code=None):
        r = run_tool(CLOSEOUT, list(args), self.p)
        if code is not None:
            self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        return r.stdout

    def status(self, out, name):
        for line in out.split("\n"):
            parts = line.split()
            if len(parts) > 1 and parts[1] == name:
                return parts[0]
        self.fail("no line for %s in:\n%s" % (name, out))

    def test_clean_tree_passes(self):
        out = self.run_check(code=0)
        for name in ("measure-marker", "backup-files", "createform", "new-form", "build-log", "data-module"):
            self.assertEqual(self.status(out, name), "OK", out)

    def test_measure_marker_left(self):
        self.replace("Sample.pas", "  X := 0;\r\n", "  X := 0;\r\n  Log(GetTickCount64); // X-MEASURE\r\n")
        self.build_log()
        out = self.run_check(code=1)
        self.assertEqual(self.status(out, "measure-marker"), "FAIL")
        self.assertIn("Sample.pas:29", out)

    def test_backup_file_even_if_ignored(self):
        with open(os.path.join(self.p.dir, ".gitignore"), "w") as f:
            f.write("*.bak\n")
        self.write("Sample.pas.bak", "x\n")
        self.write("Sample.bak", "x\n")
        self.write("Project.exe.bak", "x\n")            # an exe packer's backup on every build: not reported
        out = self.run_check(code=1)
        self.assertEqual(self.status(out, "backup-files"), "FAIL")
        self.assertIn("2 untracked .bak", out)
        self.assertIn("Sample.pas.bak", out)
        self.assertIn("Sample.bak", out)
        self.assertNotIn("Project.exe.bak", out)

    def test_build_product_backup_ignored(self):
        self.write("Project.exe.bak", "x\n")
        self.assertEqual(self.status(self.run_check(code=0), "backup-files"), "OK")

    def test_added_createform(self):
        self.replace("Project.dpr", "  Application.Run;", "  Application.CreateForm(TForm2, Form2);\r\n  Application.Run;")
        self.build_log()
        out = self.run_check(code=1)
        self.assertEqual(self.status(out, "createform"), "FAIL")
        self.assertIn("Project.dpr:9", out)

    def test_new_form_registration(self):
        self.write("Form2.pas", FORM_PAS)
        self.write("Form2.dfm", FORM_DFM, encoding="ascii")
        self.build_log()
        out = self.run_check(code=1)
        self.assertEqual(self.status(out, "new-form"), "FAIL")
        self.assertIn("unit in .dpr uses", out)
        self.assertIn("<Form>Form2</Form>", out)

        self.replace("Project.dpr", "  Sample in 'Sample.pas';", "  Sample in 'Sample.pas',\r\n  Form2 in 'Form2.pas' {Form2};")
        with open(os.path.join(self.p.dir, "Project.dproj"), "w", encoding="utf-8") as f:
            f.write(DPROJ.replace("<ItemGroup>", "<ItemGroup>\n    <DCCReference Include=\"Form2.pas\"><Form>Form2</Form>"
                                  "</DCCReference>"))
        self.build_log()
        out = self.run_check(code=0)
        self.assertEqual(self.status(out, "new-form"), "OK", out)

    def test_new_data_module_registered_the_ide_way(self):
        # the IDE writes {DmMain: TDataModule} for a data module (and {Frame1: TFrame} for a frame); it used to FAIL
        self.write("DmMain.pas", DATA_MODULE_PAS.replace("unit Data;", "unit DmMain;"))
        self.write("DmMain.dfm", "object DmMain: TDM\n  Height = 100\nend\n", encoding="ascii")
        self.replace("Project.dpr", "  Sample in 'Sample.pas';",
                     "  Sample in 'Sample.pas',\r\n  DmMain in 'DmMain.pas' {DmMain: TDataModule};")
        with open(os.path.join(self.p.dir, "Project.dproj"), "w", encoding="utf-8") as f:
            f.write(DPROJ.replace("<ItemGroup>", "<ItemGroup>\n    <DCCReference Include=\"DmMain.pas\"><Form>DmMain</Form>"
                                  "<DesignClass>TDataModule</DesignClass></DCCReference>"))
        self.build_log()
        self.assertEqual(self.status(self.run_check(), "new-form"), "OK")

    def test_external_diff_tool_does_not_hide_createform(self):
        git(self.p, "config", "diff.external", "echo")
        self.replace("Project.dpr", "  Application.Run;", "  Application.CreateForm(TForm2, Form2);\r\n  Application.Run;")
        self.build_log()
        self.assertEqual(self.status(self.run_check(code=1), "createform"), "FAIL")

    def test_build_log_older_than_change(self):
        self.append("Sample.pas", "// change\n")
        out = self.run_check(code=1)
        self.assertEqual(self.status(out, "build-log"), "FAIL")
        self.assertIn("no build log", out)
        self.build_log(after_changes=False)
        out = self.run_check(code=1)
        self.assertIn("changed after the last build", out)
        self.build_log()
        self.assertEqual(self.status(self.run_check(code=0), "build-log"), "OK")

    def test_data_module_is_a_note(self):
        self.write("Data.pas", DATA_MODULE_PAS)
        self.build_log()
        out = self.run_check(code=0)
        self.assertEqual(self.status(out, "data-module"), "NOTE")
        self.assertIn("Data.pas", out)

    def review_log(self, *rows, log=True):
        folder = os.path.join(self.p.dir, "personal", "plans")
        os.makedirs(folder, exist_ok=True)
        plan = os.path.join(folder, "T-1-plan.md")
        with open(plan, "w", encoding="utf-8") as f:
            f.write("<!-- plan:items -->\n1. Change First.\n")
        if log:
            with open(os.path.join(ROOT, ".claude", "templates", "reviews.md"), encoding="utf-8") as f:
                text = f.read()
            with open(os.path.join(folder, "T-1-reviews.md"), "w", encoding="utf-8") as f:
                f.write(text + "".join(r + "\n" for r in rows))
        return plan

    def test_review_log_skipped_without_plan(self):
        self.assertEqual(self.status(self.run_check(code=0), "review-log"), "SKIP")

    def test_review_log_missing(self):
        plan = self.review_log(log=False)
        out = self.run_check("--plan", plan, code=1)
        self.assertEqual(self.status(out, "review-log"), "FAIL")
        self.assertIn("T-1-reviews.md", out)

    def test_review_log_needs_close_out_row_today(self):
        today = datetime.date.today().isoformat()
        plan = self.review_log("| 2026-01-02 | multi-review | 1 | devils-advocate | 4 | 2 | 1 | 0 | plan step 3 added |")
        out = self.run_check("--plan", plan, code=1)
        self.assertIn("no close-out row dated %s" % today, out)

        plan = self.review_log("| 2026-01-02 | multi-review | 1 | devils-advocate | 4 | 2 | 1 | 0 | SQL a \\|\\| b |",
                               "| %s | close-out | 1 | closeout-auditor | 3 | 1 | 0 | 0 | one copy missed |" % today)
        out = self.run_check("--plan", plan, code=0)
        self.assertEqual(self.status(out, "review-log"), "OK", out)
        self.assertIn("2 row(s)", out)

    def test_review_log_malformed_rows_listed(self):
        today = datetime.date.today().isoformat()
        plan = self.review_log("| %s | close-out | 1 | closeout-auditor | 3 | 1 | 0 | 0 | ok |" % today,
                               "| 02.01.2026 | review | 1 | scope-counter | 2 | 1 | 0 | 0 | date |",
                               "| %s | audit | 1 | closeout-auditor | 2 | 3 | 0 | 0 | step, counts |" % today,
                               "| %s | review | 1 | scope-counter | 2 | 1 | 0 | 0 | a | b |" % today)
        out = self.run_check("--plan", plan, code=1)
        self.assertIn("3 problem(s)", out)
        self.assertIn("date is not YYYY-MM-DD", out)
        self.assertIn("step is not one of", out)
        self.assertIn("cannot exceed Findings", out)
        self.assertIn("10 cells instead of 9", out)

    def test_base_covers_committed_work(self):
        self.replace("Project.dpr", "  Application.Run;", "  Application.CreateForm(TForm2, Form2);\r\n  Application.Run;")
        git(self.p, "commit", "-q", "-am", "job")
        self.build_log()
        self.assertEqual(self.status(self.run_check(code=0), "createform"), "OK")
        out = self.run_check("--base", "HEAD~1", code=1)
        self.assertEqual(self.status(out, "createform"), "FAIL")


if __name__ == "__main__":
    unittest.main()
