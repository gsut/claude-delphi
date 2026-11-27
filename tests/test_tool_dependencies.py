"""The tool dependency list in docs/installation.md must be complete: a tool copied with only the files that list names
must start. (A selective copy into a real project failed with ModuleNotFoundError because a dependency was missing from
the instructions.) The Turkish installation guide must give the same list."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import ROOT, TOOLS


def documented(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    deps = {}
    for tool, needs in re.findall(r"`(\w+)` → ((?:`\w+`(?:, )?)+)", text):
        deps[tool] = re.findall(r"`(\w+)`", needs)
    return deps


def closure(deps, tool):
    out, todo = set(), [tool]
    while todo:
        t = todo.pop()
        for d in deps.get(t, []):
            if d not in out:
                out.add(d)
                todo.append(d)
    return out


class ToolDependencyTest(unittest.TestCase):
    def test_each_tool_starts_with_its_documented_dependencies_only(self):
        deps = documented(os.path.join(ROOT, "docs", "installation.md"))
        self.assertIn("pas_edit", deps)
        for name in sorted(os.listdir(TOOLS)):
            if not name.endswith(".py"):
                continue
            tool = name[:-3]
            with self.subTest(tool=tool):
                folder = tempfile.mkdtemp(prefix="claude-delphi-deps-")
                try:
                    for t in {tool} | closure(deps, tool):
                        shutil.copy(os.path.join(TOOLS, t + ".py"), folder)
                    r = subprocess.run([sys.executable, "-I", os.path.join(folder, name), "--help"], capture_output=True,
                                       text=True, encoding="utf-8", cwd=folder)
                    self.assertNotIn("ModuleNotFoundError", r.stderr,
                                     "%s needs a module the installation guide does not list" % tool)
                finally:
                    shutil.rmtree(folder, ignore_errors=True)

    def test_turkish_guide_gives_the_same_list(self):
        self.assertEqual(documented(os.path.join(ROOT, "docs", "tr", "kurulum.md")),
                         documented(os.path.join(ROOT, "docs", "installation.md")))


if __name__ == "__main__":
    unittest.main()
