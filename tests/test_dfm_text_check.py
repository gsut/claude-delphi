import os
import shutil
import tempfile
import unittest

from helpers import BINARY_DFM, TEXT_DFM, TOOLS, run_tool

DFM_TEXT_CHECK = os.path.join(TOOLS, "dfm_text_check.py")


class DfmTextCheckTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="claude-delphi-test-")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def put(self, rel, data):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def run_check(self):
        return run_tool(DFM_TEXT_CHECK, ["--root", self.dir])

    def test_text_only_is_clean(self):
        self.put("Form1.dfm", TEXT_DFM)
        self.put("Sub/Data.dfm", b"\xef\xbb\xbf" + TEXT_DFM)   # IDE-saved UTF-8 with BOM
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("No binary DFM", r.stdout)

    def test_binary_listed(self):
        self.put("Form1.dfm", TEXT_DFM)
        self.put("Old/Form2.dfm", BINARY_DFM)
        self.put("Old/Stream.dfm", b"TPF0\x06TForm3\x05Form3\x00\x00")   # bare stream, no resource header
        r = self.run_check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("2 binary DFM", r.stdout)
        self.assertIn("Form2.dfm", r.stdout)
        self.assertIn("Stream.dfm", r.stdout)
        self.assertNotIn("Form1.dfm", r.stdout)
        self.assertIn("Text DFM", r.stdout)

    def test_history_folders_skipped(self):
        self.put("__history/Form1.dfm.~1~", BINARY_DFM)
        self.put("__history/Old.dfm", BINARY_DFM)
        self.assertEqual(self.run_check().returncode, 0)


if __name__ == "__main__":
    unittest.main()
