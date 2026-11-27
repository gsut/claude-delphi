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


def unit(body):
    return "unit U;\ninterface\nimplementation\n" + body + "end.\n"


class LexerConstructsTest(unittest.TestCase):
    """Constructs that made routines disappear or end early without an error (found by independent reviews)."""

    def spans(self, text):
        return {r.path(): (r.line, r.end_line) for r in pl.routines(text)}

    def test_short_class_declaration(self):
        text = unit("type\n  EMy = class(Exception);\nprocedure A;\nbegin\nend;\nprocedure B;\nbegin\nend;\n")
        self.assertEqual(sorted(self.spans(text)), ["A", "B"])

    def test_record_constraint_in_generic(self):
        text = unit("type\n  TX = class\n    function Get<T: record>: T;\n  end;\n"
                    "procedure A;\nbegin\nend;\n")
        self.assertIn("A", self.spans(text))

    def test_attribute_before_header(self):
        text = unit("procedure A;\nbegin\nend;\n[Test]\nprocedure B;\nbegin\nend;\n")
        self.assertEqual(sorted(self.spans(text)), ["A", "B"])

    def test_paren_star_conditional(self):
        text = unit("procedure A;\nbegin\n(*$IFDEF X*)\n  if a then\n  begin\n(*$ELSE*)\n  if b then\n  begin\n"
                    "(*$ENDIF*)\n    x := 1;\n  end;\nend;\nprocedure B;\nbegin\nend;\n")
        spans = self.spans(text)
        self.assertEqual(sorted(spans), ["A", "B"])
        self.assertEqual(spans["A"][1], line_of(text, "end;\nprocedure B"))

    def test_end_as_label_or_member_is_not_a_block_end(self):
        text = unit("procedure A;\nasm\n  jmp @@end\n@@end:\n  ret\nend;\n"
                    "procedure B;\nbegin\n  R := Sheet.Cells[1, 1].End[xlUp].Row;\n  x := 1;\nend;\n")
        spans = self.spans(text)
        self.assertEqual(spans["A"][1], line_of(text, "end;\nprocedure B"))
        self.assertEqual(spans["B"][1], line_of(text, "end;\nend."))

    def test_inline_record_variable(self):
        text = unit("procedure A;\nbegin\n  var R: record\n    X: Integer;\n  end;\n  R.X := 1;\nend;\n"
                    "procedure B;\nbegin\nend;\n")
        spans = self.spans(text)
        self.assertEqual(spans["A"][1], line_of(text, "end;\nprocedure B"))

    def test_nested_generic_class_name(self):
        text = unit("procedure TFoo<TPair<K, V>>.Bar;\nbegin\nend;\n")
        self.assertEqual(list(self.spans(text)), ["TFoo.Bar"])


if __name__ == "__main__":
    unittest.main()
