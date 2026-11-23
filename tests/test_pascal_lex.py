import os
import sys
import unittest

from helpers import SAMPLE_PAS, TOOLS

sys.path.insert(0, TOOLS)
import pascal_lex as pl  # noqa: E402


def line_of(text, needle, nth=1):
    pos = -1
    for _ in range(nth):
        pos = text.index(needle, pos + 1)
    return text.count("\n", 0, pos) + 1


class PascalLexTest(unittest.TestCase):
    def setUp(self):
        self.rs = pl.routines(SAMPLE_PAS)

    def test_routines_and_nesting(self):
        names = [r.path() for r in self.rs]
        self.assertEqual(names, ["TForm1.First", "TForm1.First > Inner", "TForm1.Second"])

    def test_boundaries(self):
        first, inner, second = self.rs
        self.assertEqual(first.line, line_of(SAMPLE_PAS, "procedure TForm1.First;"))
        self.assertEqual(first.end_line, line_of(SAMPLE_PAS, "end;\n\nprocedure TForm1.Second"))
        self.assertEqual(inner.end_line, line_of(SAMPLE_PAS, "  Result := N * 2;") + 1)
        self.assertEqual(second.end_line, line_of(SAMPLE_PAS, "end;\n\nend."))

    def test_alt_branch_tokens_are_marked(self):
        toks = pl.tokenize(SAMPLE_PAS)
        alt_numbers = [t.text for t in toks if t.alt and t.kind == "number"]
        self.assertEqual(alt_numbers, ["1"])            # "if X = 1" in the {$ELSE} branch

    def test_text_after_final_end_is_ignored(self):
        self.assertEqual(pl.tokenize(SAMPLE_PAS)[-1].text, ".")

    def test_find_routine(self):
        self.assertEqual(len(pl.find_routine(self.rs, "Inner")), 1)
        self.assertEqual(len(pl.find_routine(self.rs, "tform1.first")), 1)
        self.assertEqual(len(pl.find_routine(self.rs, "TForm1.First > Inner")), 1)
        self.assertEqual(len(pl.find_routine(self.rs, "Missing")), 0)

    def test_enclosing(self):
        off = SAMPLE_PAS.index("Result := N * 2")
        self.assertEqual(pl.enclosing(self.rs, off).short, "Inner")

    def test_unbalanced_raises(self):
        with self.assertRaises(pl.ParseError):
            # three blocks opened, two closed (the final "end." closes the second)
            pl.routines("unit U;\ninterface\nimplementation\nprocedure P;\nbegin\n  begin\n  begin\nend;\nend.\n")


if __name__ == "__main__":
    unittest.main()
