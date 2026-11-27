import json
import os
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
    # found by an independent reliability review: these passed before
    ('echo x > "Unit1.pas"', True),
    ("echo x > 'My Unit.pas'", True),
    ('echo x | tee "Unit1.pas"', True),
    ("echo x>Unit1.pas", True),
    ("echo x >| Unit1.pas", True),
    ("echo x | tee out.txt Unit1.pas", True),
    ("/usr/bin/sed -i s/a/b/ Unit1.pas", True),
    ('"sed" -i s/a/b/ Unit1.pas', True),
    ("perl -0pi -e 's/a/b/' Unit1.pas", True),
    ('python -Ic "print(1)"', True),
    ('python -uc "print(1)"', True),
    ('python -c"print(1)"', True),
    ("python<<EOF\nprint(1)\nEOF", True),
    ("echo 'print(1)' | python", True),
    ('pythonw -c "print(1)"', True),
    ("psql -wU app_owner -d db", True),
    ("gh -R owner/repo pr create -t x", True),
    ("gh pr -R owner/repo create -t x", True),
    ("gh pr --repo o/r merge 5", True),
    ("gh issue -R o/r close 5", True),
    ("gh ssh-key add key.pub", True),
    ("gh pr revert 5", True),
    # ... and these were refused although they only read
    ("grep -rn 'use sed -i here' README.md", False),
    ("perl script.pl -input Unit1.pas", False),
    ("gh repo deploy-key list", False),
    ("cat a.pas 2>&1 | head", False),
    ("which python", False),
    ("python -m json.tool .claude/claude-delphi.json", False),
    ('grep -rn "x > y" Unit1.pas', False),
]

# The PowerShell tool gets rules 1-5 too (and the PowerShell ways of writing a file); before, it was not checked at all.
POWERSHELL_CASES = [
    ("'x' | Set-Content Unit1.pas", True),
    ("Set-Content -Path 'My Unit.pas' -Value x", True),
    ("Get-Content a.txt | Out-File -Encoding utf8 notes.md", True),
    ("Add-Content Unit1.dfm 'x'", True),
    ("[IO.File]::WriteAllText('Unit1.pas', 'x')", True),
    ("echo x > Unit1.pas", True),
    ("psql -U app_owner -d db -c 'delete from t'", True),
    ('python -c "print(1)"', True),
    ("gh pr create --title x", True),
    ("Get-Content Unit1.pas | Select-Object -First 5", False),
    ("'x' | Set-Content out.txt", False),
    ("git log --oneline -3", False),
]


# Commands of a read-only agent (agent_type in readonly_agents): (command, expected to be denied).
# The denied ones write or run something; most come from two independent reviews of the plan, several were run for real.
READONLY_CASES = [
    # command substitution, also inside double quotes
    ("git log -1 $(touch pwned.txt)", True),
    ("git log -1 `touch pwned.txt`", True),
    ('cat "$(python x.py)"', True),
    ("cat <(touch x)", True),
    ("grep -n '$(not expanded)' Unit1.pas", False),
    # redirection: into a file no, /dev/null and fd copies yes
    ("git diff > out.txt", True),
    ("grep x Unit1.pas>out.txt", True),
    ("git diff --ignore-cr-at-eol 2>&1 | head -50", False),
    ("cat a.pas >&2", False),
    ("grep -rn x . 2>/dev/null", False),
    ("ls &>/dev/null", False),
    ("grep -rn 'a > b' .", False),
    # programs that write or run others
    ("touch x", True),
    ("rm -f a.txt", True),
    ("cp a.pas b.pas", True),
    ("grep -l x *.pas | xargs git show", True),
    ("bash -c 'git log'", True),
    ("awk '{print > \"f\"}' a.txt", True),
    ("echo x | tee a.txt", True),
    ("GIT_EXTERNAL_DIFF=./x.sh git diff", True),
    ("source ./env.sh", True),
    # git: reading subcommands only, no option that writes or runs
    ("git diff --output=Unit1.pas", True),
    ("git log -1 --output out.txt", True),
    ("git show --output=x HEAD", True),
    ("git grep -O'touch PWNED' -e unit", True),
    ("git grep --open-files-in-pager=vim x", True),
    ("git diff --ext-diff", True),
    ("git -c core.pager=x log", True),
    ("git checkout -- Unit1.pas", True),
    ("git stash", True),
    ("git hash-object -w a.pas", True),
    ("git hash-object personal/plans/1-plan.md", False),
    ("git log --oneline -5", False),
    ("git diff -w --stat", False),
    ("git blame -L 10,20 Unit1.pas", False),
    ("git grep -n FieldByName -- '*.pas'", False),
    ("git status --short", False),
    # find, sed, sort, uniq, rg
    ("find . -name A.pas -fprint C.txt", True),
    ("find . -name '*.bak' -delete", True),
    ("find . -name '*.pas' -exec grep -l x {} ;", True),
    ("find . -name '*.dfm' -ok rm {} ;", True),
    ("find . -name '*.dfm' -newer a.pas", False),
    ("sed -n 10,20p Unit1.pas", False),
    ("sed -n '$p' Unit1.pas", False),
    ("sed -n '/x/w out.txt' Unit1.pas", True),
    ("sed 's/a/b/' Unit1.pas", True),
    ("sed -i s/a/b/ notes.txt", True),
    ("grep -rn x . | sort | uniq -d", False),
    ("sort -o out.txt a.txt", True),
    ("uniq a.txt b.txt", True),
    ("rg --pre ./evil.sh x", True),
    ("rg -n FieldByName", False),
    # shell structure that only reads
    ("cd /c/proj && git log -5", False),
    ("for f in *.dfm; do grep -c DataSource $f; done", False),
    ("if grep -q x a.pas; then echo yes; fi", False),
    ("wc -l *.pas | tail -1", False),
    # python: only the read-only tools
    ("python tools/pas_callers.py TForm1.First", False),
    ('python -I "C:/proj/tools/diff_routines.py" --plan p.md', False),
    ("py tools/closeout_check.py --plan p.md", False),
    ("python tools/pas_edit.py spec.json", True),
    ("python tools/pg_fingerprint.py take 42 before.json", True),
    ("python scripts/fix.py", True),
    ("python -m http.server", True),
    # database: reading yes, local output files no
    ('psql -U readonly -c "select count(*) from t"', False),
    ('psql -U readonly -o out.txt -c "select 1"', True),
    ('psql -U readonly -c "\\copy t to x.csv"', True),
    ("sqlcmd -S srv -U readonly -o out.txt -Q x", True),
    ("mysql -u readonly --tee=log.txt db", True),
    ("psql -U app_owner -c 'select 1'", True),   # the general rule still applies
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

    def decision(self, command, **extra):
        payload = dict({"tool_name": "Bash", "tool_input": {"command": command}}, **extra)
        out = run_hook("command_guard.py", payload, self.project)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision"), out

    def test_powershell_cases(self):
        for command, denied in POWERSHELL_CASES:
            with self.subTest(command=command):
                out = run_hook("command_guard.py", {"tool_name": "PowerShell", "tool_input": {"command": command}},
                               self.project)
                decision = (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")
                self.assertEqual(decision == "deny", denied, out)

    def test_readonly_agent_may_not_use_powershell(self):
        self.assertEqual(self.decision("git log -1", tool_name="PowerShell", agent_type="scope-counter")[0], "deny")

    def test_settings_with_bom_are_used(self):
        p = TempProject()
        try:
            with open(os.path.join(p.dir, ".claude", "claude-delphi.json"), "wb") as f:
                f.write(b"\xef\xbb\xbf" + json.dumps(SETTINGS).encode("utf-8"))
            out = run_hook("command_guard.py", {"tool_name": "Bash", "tool_input": {"command": "psql -U app_owner"}}, p)
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        finally:
            p.close()

    def test_broken_settings_refuse_every_command(self):
        # before: a trailing comma silently switched the write-user rule off
        p = TempProject()
        try:
            with open(os.path.join(p.dir, ".claude", "claude-delphi.json"), "w", encoding="utf-8") as f:
                f.write('{"write_db_users": ["app_owner"],}')
            out = run_hook("command_guard.py", {"tool_name": "Bash", "tool_input": {"command": "ls"}}, p)
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertIn("cannot be read", out["hookSpecificOutput"]["permissionDecisionReason"])
        finally:
            p.close()

    def test_unreadable_input_is_refused(self):
        for raw in (b"not json", b"[1]", b"\xff\xfe"):
            with self.subTest(raw=raw):
                out = run_hook("command_guard.py", None, self.project, raw=raw)
                self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_non_ascii_command_is_checked(self):
        decision, out = self.decision("echo x > Müşteri.pas")
        self.assertEqual(decision, "deny", out)

    def test_readonly_agent_cases(self):
        for command, denied in READONLY_CASES:
            with self.subTest(command=command):
                decision, out = self.decision(command, agent_type="scope-counter", agent_id="a1")
                self.assertEqual(decision == "deny", denied, out)

    def test_readonly_rule_only_for_listed_agents(self):
        # the main session (no agent_type) and other agents are not limited by rule 6
        for extra in ({}, {"agent_type": "Explore", "agent_id": "a2"}):
            with self.subTest(extra=extra):
                self.assertIsNone(self.decision("touch x", **extra)[0])
        # a plugin agent arrives as "plugin:name"
        self.assertEqual(self.decision("touch x", agent_type="claude-delphi:devils-advocate")[0], "deny")

    def test_readonly_agents_setting(self):
        p = TempProject({"readonly_agents": ["my-reviewer"]})
        try:
            for agent, denied in (("my-reviewer", True), ("scope-counter", False)):
                out = run_hook("command_guard.py", {"tool_name": "Bash", "tool_input": {"command": "touch x"},
                                                    "agent_type": agent}, p)
                self.assertEqual((out or {}).get("hookSpecificOutput", {}).get("permissionDecision") == "deny", denied)
        finally:
            p.close()

    def test_crash_denies(self):
        # an unexpected input shape makes the checks fail: the command must be refused, not let through
        decision, out = self.decision(["not", "a", "string"])
        self.assertEqual(decision, "deny", out)
        self.assertIn("could not check", out["hookSpecificOutput"]["permissionDecisionReason"])

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
