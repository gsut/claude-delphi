import json
import os
import subprocess
import sys
import unittest

from helpers import BINARY_DFM, HOOKS, TEXT_DFM, TempProject


def run_session(project):
    r = subprocess.run([sys.executable, "-I", os.path.join(HOOKS, "session_check.py")],
                       input=json.dumps({"hook_event_name": "SessionStart", "source": "startup", "cwd": project.dir}),
                       capture_output=True, text=True, encoding="utf-8", env=project.env(), cwd=project.dir)
    return r


class SessionCheckTest(unittest.TestCase):
    def tearDown(self):
        self.project.close()

    def put(self, rel, data):
        path = os.path.join(self.project.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def test_broken_settings_are_announced(self):
        self.project = TempProject({})
        self.put(os.path.join(".claude", "claude-delphi.json"), b'{"warn_binary_dfm": true,}')
        r = run_session(self.project)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("cannot be read", r.stdout)

    def test_silent_when_all_text(self):
        self.project = TempProject({})
        self.put("Form1.dfm", TEXT_DFM)
        r = run_session(self.project)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_binary_dfm_reported(self):
        self.project = TempProject({})
        self.put("Form1.dfm", TEXT_DFM)
        self.put("Old/Form2.dfm", BINARY_DFM)
        self.put("__history/Form3.dfm", BINARY_DFM)        # IDE history is skipped
        r = run_session(self.project)
        self.assertEqual(r.returncode, 0)
        self.assertIn("1 binary DFM", r.stdout)
        self.assertIn("Form2.dfm", r.stdout)
        self.assertNotIn("Form3.dfm", r.stdout)
        self.assertIn("Text DFM", r.stdout)

    def test_can_be_turned_off(self):
        self.project = TempProject({"warn_binary_dfm": False})
        self.put("Form2.dfm", BINARY_DFM)
        r = run_session(self.project)
        self.assertEqual(r.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
