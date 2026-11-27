"""Checks the sub-agent definitions in .claude/agents/.

Claude Code ignores a frontmatter field it does not recognise without an error, and an agent without a `tools` line
inherits every tool (Edit, Write, PowerShell, Agent, MCP ...). The review agents must stay read-only, so a typo or a deleted
line must fail here instead of silently widening what they can do.
"""
import glob
import json
import os
import re
import sys
import unittest

from helpers import HOOKS, ROOT

AGENTS = os.path.join(ROOT, ".claude", "agents")
SKILLS = os.path.join(ROOT, ".claude", "skills")
READ_ONLY_TOOLS = {"Read", "Grep", "Glob", "Bash"}
KEYS = {"name", "description", "tools"}            # the keys this repository uses; extend when a new one is adopted


def frontmatter(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def skill_text():
    parts = []
    for path in glob.glob(os.path.join(SKILLS, "*", "SKILL.md")):
        with open(path, encoding="utf-8") as f:
            parts.append(f.read())
    return "\n".join(parts)


class AgentDefinitionTest(unittest.TestCase):
    def setUp(self):
        self.paths = sorted(glob.glob(os.path.join(AGENTS, "*.md")))
        self.assertTrue(self.paths, "no agent definitions found")

    def test_frontmatter_keys_and_name(self):
        for path in self.paths:
            with self.subTest(agent=os.path.basename(path)):
                fields = frontmatter(path)
                self.assertIsNotNone(fields, "no frontmatter")
                self.assertEqual(set(fields) - KEYS, set(), "unknown key (Claude Code would ignore it silently)")
                self.assertEqual(fields.get("name"), os.path.splitext(os.path.basename(path))[0])
                self.assertTrue(fields.get("description"))

    def test_tools_are_read_only(self):
        for path in self.paths:
            with self.subTest(agent=os.path.basename(path)):
                tools = frontmatter(path).get("tools")
                self.assertTrue(tools, "no tools line: the agent would inherit every tool")
                listed = {t.strip() for t in tools.split(",") if t.strip()}
                self.assertLessEqual(listed, READ_ONLY_TOOLS)

    def test_every_agent_is_read_only_in_command_guard(self):
        # a new or renamed agent missing from readonly_agents would silently run without the read-only trip wire
        names = sorted(os.path.splitext(os.path.basename(p))[0] for p in self.paths)
        sys.path.insert(0, HOOKS)
        try:
            import command_guard
        finally:
            sys.path.remove(HOOKS)
        self.assertEqual(sorted(command_guard.DEFAULTS["readonly_agents"]), names)
        with open(os.path.join(ROOT, "examples", "claude-delphi.json"), encoding="utf-8") as f:
            self.assertEqual(sorted(json.load(f)["readonly_agents"]), names)

    def test_every_agent_is_used_by_a_skill(self):
        text = skill_text()
        for path in self.paths:
            name = os.path.splitext(os.path.basename(path))[0]
            with self.subTest(agent=name):
                self.assertIn("`%s`" % name, text)


if __name__ == "__main__":
    unittest.main()
