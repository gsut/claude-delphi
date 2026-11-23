import json
import os
import unittest

from helpers import TOOLS, TempProject, run_tool, write_sample

PAS_EDIT = os.path.join(TOOLS, "pas_edit.py")
ANCHOR = "  Result := False; // Ölçüm\n"     # at line start once in First and once in Second (plus once more indented)


class PasEditTest(unittest.TestCase):
    def setUp(self):
        self.project = TempProject({"source_encoding": "cp1254"})
        self.path = write_sample(self.project.dir)
        with open(self.path, "rb") as f:
            self.before = f.read()

    def tearDown(self):
        self.project.close()

    def edit(self, edits, *extra, **spec):
        spec.update(file=self.path, edits=edits)
        p = os.path.join(self.project.dir, "spec.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False)
        return run_tool(PAS_EDIT, [p] + list(extra), self.project)

    def after(self):
        with open(self.path, "rb") as f:
            return f.read()

    def test_ambiguous_anchor_refused(self):
        r = self.edit([{"old": ANCHOR, "new": "x\n"}])
        self.assertEqual(r.returncode, 1)
        self.assertIn("occurs 2 times", r.stdout)
        self.assertEqual(self.after(), self.before)

    def test_routine_scope_and_encoding_kept(self):
        r = self.edit([{"old": ANCHOR, "new": "  // Değişti. AB - 2026-01-31\n" + ANCHOR, "routine": "TForm1.Second"}],
                      additions_only=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        data = self.after()
        self.assertIn("// Değişti. AB - 2026-01-31\r\n".encode("cp1254"), data)
        self.assertEqual(data.count(b"\n"), self.before.count(b"\n") + 1)
        self.assertEqual(data.count(b"\n"), data.count(b"\r\n"))     # still CRLF only
        second = data.index(b"procedure TForm1.Second")
        self.assertGreater(data.index("Değişti".encode("cp1254")), second)

    def test_whole_line_anchor_does_not_match_inside_a_deeper_line(self):
        # "  Result..." also occurs inside "    Result..." (try/finally of Second); that must not count or be split
        r = self.edit([{"old": ANCHOR, "new": "  // x\n" + ANCHOR, "routine": "Second"}], additions_only=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("    Result := False; // Ölçüm\r\n".encode("cp1254"), self.after())

    def test_nested_routine_path(self):
        r = self.edit([{"old": "  Result := N * 2;\n", "new": "  Result := N * 3;\n", "routine": "TForm1.First > Inner"}])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn(b"Result := N * 3;", self.after())

    def test_additions_only_refuses_changes(self):
        r = self.edit([{"old": "  Result := N * 2;\n", "new": "  Result := N * 3;\n", "routine": "Inner"}],
                      additions_only=True)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.after(), self.before)

    def test_unknown_routine_refused(self):
        r = self.edit([{"old": ANCHOR, "new": "x\n", "routine": "Missing"}])
        self.assertEqual(r.returncode, 1)
        self.assertIn("matches 0 routines", r.stdout)

    def test_character_outside_code_page_refused(self):
        r = self.edit([{"old": ANCHOR, "new": "  // 中\n" + ANCHOR, "routine": "Second"}])
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.after(), self.before)

    def test_dry_run_writes_nothing(self):
        r = self.edit([{"old": ANCHOR, "new": "  // x\n" + ANCHOR, "routine": "Second"}], "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("dry run", r.stdout)
        self.assertEqual(self.after(), self.before)

    def test_all_or_nothing(self):
        r = self.edit([{"old": ANCHOR, "new": "  // ok\n" + ANCHOR, "routine": "Second"},
                       {"old": "no such text\n", "new": "x\n"}])
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.after(), self.before)

    def test_dfm_must_stay_ascii(self):
        dfm = os.path.join(self.project.dir, "Form1.dfm")
        with open(dfm, "wb") as f:
            f.write(b"object Form1: TForm1\r\n  Caption = 'Form'\r\nend\r\n")
        spec = os.path.join(self.project.dir, "dfm.json")
        with open(spec, "w", encoding="utf-8") as f:
            json.dump({"file": dfm, "edits": [{"old": "'Form'", "new": "'Ölçüm'"}]}, f, ensure_ascii=False)
        r = run_tool(PAS_EDIT, [spec], self.project)
        self.assertEqual(r.returncode, 1)
        self.assertIn("ASCII", r.stdout)


if __name__ == "__main__":
    unittest.main()
