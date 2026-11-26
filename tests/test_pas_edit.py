import json
import os
import unittest

from helpers import BINARY_DFM, TOOLS, TempProject, run_tool, write_sample

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

    def test_reverse_restores_the_file(self):
        edits = [{"old": ANCHOR, "new": "  // Ölçüm başı\n" + ANCHOR, "routine": "TForm1.First"},
                 {"old": ANCHOR, "new": ANCHOR + "  // Ölçüm sonu\n", "routine": "TForm1.Second"}]
        r = self.edit(edits, additions_only=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotEqual(self.after(), self.before)
        r = self.edit(edits, "--reverse", additions_only=True)
        self.assertEqual(r.returncode, 0, r.stdout)
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

    def test_anchor_ending_with_the_routines_final_end(self):
        old = ANCHOR + "end;\n"
        r = self.edit([{"old": old, "new": ANCHOR + "  // x\nend;\n", "routine": "TForm1.Second"}], additions_only=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("  Result := False; // Ölçüm\r\n  // x\r\nend;\r\n".encode("cp1254"), self.after())

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

    def test_binary_dfm_refused(self):
        dfm = os.path.join(self.project.dir, "Bin.dfm")
        with open(dfm, "wb") as f:
            f.write(BINARY_DFM)
        spec = os.path.join(self.project.dir, "bin.json")
        with open(spec, "w", encoding="utf-8") as f:
            json.dump({"file": dfm, "edits": [{"old": "Form1", "new": "Form2"}]}, f)
        r = run_tool(PAS_EDIT, [spec], self.project)
        self.assertEqual(r.returncode, 1)
        self.assertIn("binary DFM", r.stdout)
        with open(dfm, "rb") as f:
            self.assertEqual(f.read(), BINARY_DFM)

    def test_dfm_with_existing_utf8_can_get_ascii_additions(self):
        # IDE-saved DFMs can be UTF-8 with BOM and already contain non-ASCII text; adding ASCII must still work
        dfm = os.path.join(self.project.dir, "Data.dfm")
        body = "object Dm: TDataModule\r\n  object Q: TQuery\r\n    SQL.Strings = ('-- Ölçüm')\r\n  end\r\nend\r\n"
        with open(dfm, "wb") as f:
            f.write(b"\xef\xbb\xbf" + body.encode("utf-8"))
        spec = os.path.join(self.project.dir, "dfm2.json")
        with open(spec, "w", encoding="utf-8") as f:
            json.dump({"file": dfm, "edits": [{"old": "  end\nend\n",
                                                "new": "  end\n  object Q2: TQuery\n  end\nend\n"}]}, f)
        r = run_tool(PAS_EDIT, [spec], self.project)
        self.assertEqual(r.returncode, 0, r.stdout)
        with open(dfm, "rb") as f:
            data = f.read()
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        self.assertIn("-- Ölçüm".encode("utf-8"), data)
        self.assertIn(b"  object Q2: TQuery\r\n", data)


if __name__ == "__main__":
    unittest.main()
