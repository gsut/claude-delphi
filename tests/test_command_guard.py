import unittest

from helpers import TempProject, run_hook

SETTINGS = {"write_db_users": ["app_owner"], "scripts_dir": "scripts/"}

# (command, expected to be denied)
CASES = [
    ('python -c "print(1)"', True),
    ("python - <<EOF\nprint(1)\nEOF", True),
    ("python script.py --x", False),
    ("python -I -m py_compile a.py", False),
    ("sed -i 's/a/b/; s/c/d/' Unit1.pas", True),
    ("sed -i.bak s/a/b/ Form1.dfm", True),
    ("perl -pi -e 's/a/b/' notes.md", True),
    ("sed -n 1,5p Unit1.pas", False),
    ("sed -i s/a/b/ data.txt", False),
    ("cat x > Unit1.pas", True),
    ("echo a >> Unit1.dpr", True),
    ("cat x > out.txt 2>/dev/null", False),
    ("echo a | tee notes.md", True),
    ("grep -rn 'a > b.pas' .", False),
    # write-access database user, any client
    ('psql -U app_owner -d db -c "select 1"', True),
    ('psql -U readonly -d db -c "select 1"', False),
    ('sqlcmd -S srv -U app_owner -P x -Q "select 1"', True),
    ("sqlcmd -S srv -U readonly -P x", False),
    ("mysql -u app_owner -p db", True),
    ("mysql -uapp_owner db", True),
    ("mysql --user=app_owner db", True),
    ("mysql --user=readonly db", False),
    ("isql -user app_owner -password x db.fdb", True),
    ("isql -user SYSDBA db.fdb", False),
    ("PGUSER=app_owner psql -d db", True),
    ("ISC_USER=app_owner isql db.fdb", True),
    ('tool "Server=x;Database=d;User ID=app_owner;Password=y"', True),
    ('tool "Server=x;UID=readonly;PWD=y"', False),
    ('psql "host=x dbname=d user=app_owner"', True),
    ('psql "host=x dbname=d user=readonly"', False),
    ("psql postgresql://app_owner:pw@host/db", True),
    ("psql postgresql://readonly:pw@host/db", False),
    ("mysql -u app_owner_ro db", False),
    ('grep -rn "app_owner" docs/', False),
    # GitHub CLI: read-only for Claude
    ("gh release view v0.2.0 -R owner/repo", False),
    ("gh run list --limit 5", False),
    ("gh pr view 12 --json title", False),
    ("gh api repos/owner/repo/releases", False),
    ("gh api -X GET repos/owner/repo", False),
    ("gh auth status", False),
    ("gh release create v0.3.0 --notes x", True),
    ('"/c/Program Files/GitHub CLI/gh.exe" release delete v0.2.0', True),
    ("gh pr create --title x --body y", True),
    ("gh pr merge 12", True),
    ("gh issue comment 5 -b x", True),
    ("gh repo delete owner/x --yes", True),
    ("gh api -X POST repos/owner/repo/issues -f title=x", True),
    ("gh api repos/owner/repo/issues --method=PATCH", True),
    ("gh secret list", True),
    ("gh auth token", True),
    ("git log -1 && gh workflow run ci.yml", True),
]


class CommandGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = TempProject(SETTINGS)

    @classmethod
    def tearDownClass(cls):
        cls.project.close()

    def test_cases(self):
        for command, denied in CASES:
            with self.subTest(command=command):
                out = run_hook("command_guard.py", {"tool_name": "Bash", "tool_input": {"command": command}}, self.project)
                decision = (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")
                self.assertEqual(decision == "deny", denied, out)

    def test_other_tools_ignored(self):
        out = run_hook("command_guard.py", {"tool_name": "Write", "tool_input": {"file_path": "a > b.pas"}}, self.project)
        self.assertIsNone(out)

    def test_gh_write_can_be_allowed(self):
        p = TempProject({"forbid_gh_write": False})
        try:
            out = run_hook("command_guard.py", {"tool_name": "Bash", "tool_input": {"command": "gh pr create -t x"}}, p)
            self.assertIsNone(out)
        finally:
            p.close()

    def test_inline_python_can_be_allowed(self):
        p = TempProject({"forbid_inline_python": False})
        try:
            out = run_hook("command_guard.py", {"tool_name": "Bash", "tool_input": {"command": 'python -c "1"'}}, p)
            self.assertIsNone(out)
        finally:
            p.close()


if __name__ == "__main__":
    unittest.main()
