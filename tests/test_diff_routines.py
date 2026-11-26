import os
import subprocess
import sys
import unittest

from helpers import SAMPLE_PAS, TOOLS, TempProject, run_tool, write_sample

DIFF_ROUTINES = os.path.join(TOOLS, "diff_routines.py")

DFM = (
    "object Form1: TForm1\n"
    "  Caption = 'One'\n"
    "  object Panel1: TPanel\n"
    "    object Button1: TButton\n"
    "      Caption = 'Old'\n"
    "    end\n"
    "  end\n"
    "end\n"
)


def git(project, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   cwd=project.dir, check=True, capture_output=True)


class DiffRoutinesTest(unittest.TestCase):
    def setUp(self):
        self.p = TempProject({"source_encoding": "cp1254"}, git=True)
        # The tests must not depend on the machine's Git settings: with core.autocrlf=true (GitHub's Windows runners) a
        # file that differs only in line endings is not a change at all, and the "line endings only" case never appears.
        git(self.p, "config", "core.autocrlf", "false")
        write_sample(self.p.dir)
        write_sample(self.p.dir, "Form1.dfm", DFM, encoding="ascii")
        git(self.p, "add", ".")
        git(self.p, "commit", "-q", "-m", "base")

    def tearDown(self):
        self.p.close()

    def change(self, old, new, name="Sample.pas", encoding="cp1254"):
        path = os.path.join(self.p.dir, name)
        with open(path, "rb") as f:
            text = f.read().decode(encoding)
        self.assertIn(old, text)
        with open(path, "wb") as f:
            f.write(text.replace(old, new, 1).encode(encoding))

    def plan(self, text):
        path = os.path.join(self.p.dir, "plan.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def run_map(self, *args):
        r = run_tool(DIFF_ROUTINES, list(args), self.p)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_hunk_mapped_to_routine_and_plan(self):
        self.change("    First;\r\n", "    First;\r\n    First;\r\n")
        out = self.run_map("--plan", self.plan("Change TForm1.First only."))
        self.assertIn("TForm1.Second", out)
        self.assertIn("NOT IN PLAN", out)
        self.assertIn("not in the plan: 1", out)

    def test_routine_named_in_plan(self):
        self.change("  X := 0;\r\n", "  X := 2;\r\n")
        out = self.run_map("--plan", self.plan("Change First: start X at 2."))
        self.assertIn("TForm1.First", out)
        self.assertIn("in plan", out)
        self.assertNotIn("NOT IN PLAN", out)

    def test_nested_routine_is_innermost(self):
        self.change("  Result := N * 2;\r\n", "  Result := N * 3;\r\n")
        out = self.run_map()
        self.assertIn("Inner", out)

    def test_whitespace_only_marked(self):
        self.change("  X := 0;\r\n", "  X  :=  0;\r\n")
        self.assertIn("whitespace only", self.run_map())

    def test_line_endings_only(self):
        path = os.path.join(self.p.dir, "Sample.pas")
        with open(path, "rb") as f:
            data = f.read()
        with open(path, "wb") as f:
            f.write(data.replace(b"\r\n", b"\n"))
        self.assertIn("line endings only", self.run_map())

    def test_dfm_object_chain(self):
        self.change("Caption = 'Old'", "Caption = 'New'", name="Form1.dfm", encoding="ascii")
        self.assertIn("Form1 > Panel1 > Button1", self.run_map())

    def test_untracked_listed(self):
        write_sample(self.p.dir, "NewUnit.pas")
        self.assertIn("NewUnit.pas", self.run_map())

    def test_commit_mode(self):
        self.change("  X := 0;\r\n", "  X := 5;\r\n")
        git(self.p, "commit", "-q", "-am", "change")
        out = self.run_map("--commit", "HEAD")
        self.assertIn("HEAD^..HEAD", out)
        self.assertIn("TForm1.First", out)

    def test_no_changes(self):
        self.assertIn("No changes.", self.run_map())

    def test_root_found_from_subfolder(self):
        # without $CLAUDE_PROJECT_DIR the tool walks up to the folder holding .claude/claude-delphi.json
        self.change("  X := 0;\r\n", "  X := 3;\r\n")
        sub = os.path.join(self.p.dir, "Sub")
        os.makedirs(sub)
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run([sys.executable, DIFF_ROUTINES], cwd=sub, env=env, capture_output=True, text=True,
                           encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Sample.pas", r.stdout)
        self.assertIn("TForm1.First", r.stdout)

    def test_non_ascii_file_name(self):
        write_sample(self.p.dir, "Ölçüm.pas")
        git(self.p, "add", ".")
        git(self.p, "commit", "-q", "-m", "add")
        self.change("  X := 0;\r\n", "  X := 7;\r\n", name="Ölçüm.pas")
        out = self.run_map()
        self.assertIn("Ölçüm.pas", out)
        self.assertIn("TForm1.First", out)


if __name__ == "__main__":
    unittest.main()
