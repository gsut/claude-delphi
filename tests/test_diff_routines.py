import os
import subprocess
import sys
import unittest

from helpers import ROOT, SAMPLE_PAS, TOOLS, TempProject, run_tool, write_sample

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

    def test_marked_plan_searches_items_and_scope_only(self):
        # "Second" is named in the evidence and among the unchanged callers: with section markers that must not count
        self.change("    First;\r\n", "    First;\r\n    First;\r\n")
        marked = ("<!-- plan:hypothesis -->\r\n## Hipotez\r\nSecond calls First (Sample.pas:56).\r\n"
                  "<!-- plan:items -->\r\n## Plan maddeleri\r\n1. Change First.\r\n"
                  "<!-- plan:callers -->\r\n## Diğer çağıranlar\r\nSecond stays as it is.\r\n")
        out = self.run_map("--plan", self.plan(marked))
        self.assertIn("searched sections: items", out)
        self.assertIn("NOT IN PLAN", out)
        self.assertIn("not in the plan: 1", out)

        out = self.run_map("--plan", self.plan(marked.replace("1. Change First.", "1. Change First and Second.")))
        self.assertNotIn("NOT IN PLAN", out)

    def test_marked_plan_without_items_counts_nothing(self):
        self.change("  X := 0;\r\n", "  X := 2;\r\n")
        out = self.run_map("--plan", self.plan("<!-- plan:hypothesis -->\nFirst starts X at 0.\n"))
        self.assertIn("no plan:items / plan:scope section", out)
        self.assertIn("NOT IN PLAN", out)

    def test_unmarked_plan_reports_whole_file_search(self):
        self.change("  X := 0;\r\n", "  X := 2;\r\n")
        self.assertIn("whole plan is searched", self.run_map("--plan", self.plan("Change First.")))

    def test_scope_entries_not_changed(self):
        # Scope lists only what will change: an entry nothing touches is reported; plan:contingency is not read
        self.change("  X := 0;\r\n", "  X := 2;\r\n")
        plan = ("<!-- plan:items -->\n1. `Sample.pas` `TForm1.First`: start X at 2.\n"
                "<!-- plan:scope -->\n- `Sample.pas`: `TForm1.First`, `TForm1.Second`; `Form1.dfm` `Button1`.\n"
                "- code in backticks is not a name: `X := 2;`\n"
                "<!-- plan:contingency -->\n- only if needed: `Inner`, `Other.pas`\n")
        out = self.run_map("--plan", self.plan(plan))
        tail = out.split("but not changed:")[1]
        self.assertIn("but not changed: 3", out)
        for name in ("TForm1.Second", "Form1.dfm", "Button1"):
            self.assertIn(name, tail)
        for name in ("TForm1.First", "Sample.pas", "Inner", "Other.pas", "X := 2"):
            self.assertNotIn(name, tail)

    def test_scope_entries_found_in_dfm_and_new_unit(self):
        self.change("Caption = 'Old'", "Caption = 'New'", name="Form1.dfm", encoding="ascii")
        write_sample(self.p.dir, "NewUnit.pas")                 # untracked: its routines are all new
        plan = "<!-- plan:scope -->\n`Form1.dfm` `Button1` `Panel1` `NewUnit.pas` `TForm1.First > Inner` `Inner`\n"
        out = self.run_map("--plan", self.plan(plan))
        self.assertIn("but not changed: 0", out)

    def test_unmarked_plan_has_no_scope_check(self):
        self.change("  X := 0;\r\n", "  X := 2;\r\n")
        self.assertNotIn("but not changed", self.run_map("--plan", self.plan("Change `TForm1.Second`.")))

    def test_comment_above_routine_belongs_to_it(self):
        # a dead-code marker written right above a routine is a change of that routine for the plan check
        self.change("procedure TForm1.Second;\r\n", "// DEAD-CODE: no caller. XX - 2026-11-26\r\nprocedure TForm1.Second;\r\n")
        out = self.run_map("--plan", self.plan("<!-- plan:items -->\n1. Mark `TForm1.Second` dead.\n"))
        self.assertIn("in plan (comment above Second)", out)
        self.assertIn("not in the plan: 0", out)
        out = self.run_map("--plan", self.plan("<!-- plan:items -->\n1. Change `TForm1.First`.\n"))
        self.assertIn("NOT IN PLAN", out)

    def test_explanation_above_new_routine_belongs_to_it(self):
        # a comment added in the same hunk as the routine below it, separated by a blank line
        self.change("procedure TForm1.Second;\r\n",
                    "// Third: why it exists.\r\n// XX - 2026-11-26\r\nprocedure TForm1.Third;\r\nbegin\r\nend;\r\n\r\n"
                    "procedure TForm1.Second;\r\n")
        out = self.run_map("--plan", self.plan("<!-- plan:items -->\n1. Add `TForm1.Third`.\n"))
        self.assertIn("in plan (comment above Third)", out)
        self.assertIn("not in the plan: 0", out)

    def test_comment_above_declaration_belongs_to_it(self):
        # a comment above a declaration in the interface / a class belongs to that declaration, not to the next routine
        # body further down (it was charged to TForm1.First and reported NOT IN PLAN)
        self.change("    procedure Second;\r\n", "    // Second: why. XX - 2026-11-26\r\n    procedure Second;\r\n")
        out = self.run_map("--plan", self.plan("<!-- plan:items -->\n1. Document `TForm1.Second`.\n"))
        self.assertIn("in plan (comment above Second)", out)
        self.assertIn("not in the plan: 0", out)

    def test_comment_followed_by_other_code_belongs_to_nothing(self):
        self.change("implementation\r\n", "implementation\r\n\r\n// uses below\r\nuses SysUtils;\r\n")
        out = self.run_map("--plan", self.plan("<!-- plan:items -->\n1. Change `TForm1.First`.\n"))
        self.assertNotIn("NOT IN PLAN", out)
        self.assertNotIn("comment above", out)

    def test_class_in_scope_counts_when_a_method_changed(self):
        # a method added to the class declaration maps to unit level; the class is still "changed" through the method
        self.change("    procedure Second;\r\n", "    procedure Second;\r\n    procedure Third;\r\n")
        self.change("  X := 0;\r\n", "  X := 2;\r\n")
        out = self.run_map("--plan", self.plan("<!-- plan:scope -->\n`TForm1` `TForm1.First`\n"))
        self.assertIn("but not changed: 0", out)
        out = self.run_map("--plan", self.plan("<!-- plan:scope -->\n`TForm2`\n"))
        self.assertIn("but not changed: 1", out)

    # --- machine Git settings and odd files must not change the map (found by an independent reliability review) ---
    def test_external_diff_tool_is_ignored(self):
        git(self.p, "config", "diff.external", "echo")
        self.change("  X := 0;\r\n", "  X := 2;\r\n")
        out = self.run_map()
        self.assertIn("TForm1.First", out)
        self.assertNotIn("line endings only", out)

    def test_inter_hunk_context_does_not_charge_untouched_routines(self):
        git(self.p, "config", "diff.interHunkContext", "10")
        self.change("  X: Integer;\r\n", "  X: Int64;\r\n")         # in First's var section, above Inner
        self.change("  X := 0;\r\n", "  X := 2;\r\n")               # in First's body, below Inner
        self.assertNotIn("Inner", self.run_map())

    def test_binary_and_new_empty_files_are_named(self):
        with open(os.path.join(self.p.dir, "Form1.dfm"), "wb") as f:
            f.write(b"TPF0\x00\x01binary")
        open(os.path.join(self.p.dir, "Empty.pas"), "wb").close()
        git(self.p, "add", "Empty.pas")
        out = self.run_map()
        self.assertIn("binary content changed", out)
        self.assertIn("new empty file", out)

    def test_qualified_plan_name_does_not_cover_another_class(self):
        self.change("  X := 0;\r\n", "  X := 2;\r\n")
        for plan, expected in (("1. `TForm2.First`: x", "NOT IN PLAN"), ("1. `TForm1.First`: x", "  in plan"),
                               ("1. First: x", "  in plan")):
            with self.subTest(plan=plan):
                self.assertIn(expected, self.run_map("--plan", self.plan("<!-- plan:items -->\n" + plan + "\n")))

    def test_routines_of_a_new_unit_are_checked_against_the_plan(self):
        write_sample(self.p.dir, "NewUnit.pas")                      # untracked: Claude cannot git add
        out = self.run_map("--plan", self.plan("<!-- plan:items -->\n1. New unit with `TForm1.First`.\n"))
        self.assertIn("TForm1.First  (new, line", out)
        self.assertIn("NewUnit.pas: TForm1.Second", out)            # counted as not in the plan
        self.assertIn("NewUnit.pas: TForm1.First > Inner", out)

    def test_template_sections(self):
        sys.path.insert(0, TOOLS)
        try:
            import diff_routines
        finally:
            sys.path.remove(TOOLS)
        with open(os.path.join(ROOT, ".claude", "templates", "plan.md"), encoding="utf-8") as f:
            template = f.read()
        text, note = diff_routines.plan_text(template)
        self.assertEqual(note, "searched sections: items, scope")
        self.assertIn("TFormX.Routine", text)
        self.assertNotIn("Other callers", text)
        markers = diff_routines.PLAN_MARKER
        self.assertEqual([m.group(1) for m in map(markers.match, template.split("\n")) if m],
                         ["status", "request", "hypothesis", "items", "scope", "callers", "contingency",
                          "removed-calls", "commit-point", "assumptions", "tests"])
        # the template's own Scope example uses only backticked names, so the reverse check can read it
        files, names = diff_routines.scope_names(diff_routines.plan_sections(template)["scope"])
        self.assertEqual((files, names), (["Unit.pas", "Unit.dfm"], ["TFormX.Routine", "TFormX.Other", "Grid1"]))

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
