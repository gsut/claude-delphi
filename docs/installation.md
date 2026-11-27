# Installation and configuration

Türkçe: [tr/kurulum.md](tr/kurulum.md) · Back to the [README](../README.md)

## Requirements

No pip packages: everything uses the Python standard library.

| Requirement | Needed by | Notes |
|---|---|---|
| **Python 3.11+**, on the path as `python` | hooks, tools, `summary.py`, tests | CI runs 3.11 and 3.13 on Windows and Ubuntu; older 3.x versions may work but are not tested. `settings.json` calls `python -I …`; if the command is `python3` on Linux / macOS, change it there. |
| **Git**, on the path | `pascal_check.py` (tells new violations from old ones), tests | The project must be a Git repository. |
| **Claude Code**, a version with skills, sub-agents and SessionStart hooks | hooks, `.claude/skills/`, `.claude/agents/` | `/multi-review` starts two sub-agents in parallel. |
| **Delphi 2007 or later** (`.dproj`, `msbuild`, `rsvars.bat`) | `build/` only | The licence must include the command-line compiler; Community Edition not verified. |
| **psql** (PostgreSQL client) + a read-only user | `pg_fingerprint.py` only | Not used with other databases. |
| **Windows + Git Bash** | recommended environment | Everything was written and used there; `build.bat` is Windows-only. Hooks and tools should run on Linux (CI includes Ubuntu) but were not tried in a real Linux Delphi setup. |

## Before you start: binary DFMs

Claude, the hooks and the tools can only read and edit **text** DFMs. A binary DFM (very old projects, or "Text DFM"
switched off in the IDE) is unreadable for them, and the `.gitattributes` rule in step 9 would corrupt it. Check first:

```
python tools/dfm_text_check.py --root <project folder>
```

It lists every binary DFM and exits with 1 if there is one. Convert them before anything else: in the IDE open the form,
right-click it > **Text DFM**, save; or use Delphi's command-line converter `bin\convert.exe -i -t <file.dfm>` (run
`convert.exe` without arguments to check the options of your version). The tool never changes a file.

After installation the package keeps watching: the SessionStart hook (`session_check.py`) tells Claude at the start of
every new session (not on resume) if a binary DFM has appeared, and Claude tells you in its first answer; `pas_edit.py` refuses to edit one;
`pascal_check.py` reports one among changed files.

## Installation

All paths below are relative to the project root (the folder of your `.dpr`, which must be a Git repository).

1. Copy **all of** `hooks/*.py` to your project's `.claude/hooks/` folder (the hooks import `hook_common.py` from their own
   folder) and the **whole** `tools/` folder to a `tools/` folder in the project. The tools import each other:
   `pas_edit` → `pascal_lex`, `dfm_text_check`; `pas_callers` → `pascal_lex`, `dfm_text_check`; `diff_routines` → `pascal_lex`;
   `closeout_check` → `diff_routines`. Copying a single file breaks the others with `ModuleNotFoundError`, and copies
   updated one by one drift apart: when you update, copy the whole folder again. The hook messages refer to
   `tools/pas_edit.py` and `tools/dfm_text_check.py`.
2. Copy `examples/settings.json` to `.claude/settings.json` (merge if you have one). It wires the three hooks:
   `session_check.py` (SessionStart), `command_guard.py` (PreToolUse, Bash and PowerShell) and `pascal_check.py`
   (PreToolUse on Write / Edit to keep a snapshot of the file, PostToolUse to report). It also denies Claude Code's
   **PowerShell** tool: the `Bash(...)` deny rules (git, gh) do not apply to it, so on Windows it would bypass them. The
   hooks check PowerShell commands as well, in case you remove that rule. `python` must be on the path.
3. Copy `examples/claude-delphi.json` to `.claude/claude-delphi.json` and adjust it (table below and *Localization*).
4. Copy `.claude/skills/`, `.claude/agents/` and `.claude/templates/` (plan file and review log templates) into your
   project's `.claude/` folder.
5. Put `build/` at the project root as `build\` (the build-check skill calls `build\build.bat`; by default it builds
   `..\Project.dproj`). Set `DELPHI_RSVARS`, `DELPHI_DPROJ`, `DELPHI_CONFIG`, `DELPHI_PLATFORM` in `build.bat` (or as
   environment variables). Keep the `.bat` file CRLF. First run: `build.bat baseline`.
6. Copy `examples/CLAUDE.md` to the project root and fill in the `<…>` parts. Copy `docs/mistake-log.md` and
   `docs/delphi-pitfalls.md` to a `docs/` folder in the project: `CLAUDE.md` loads the mistake log with `@docs/mistake-log.md`,
   and it becomes the start of your own log. Documents `CLAUDE.md` mentions that you do not have yet (screen flow map, table
   → code index, the mistake log's story file) are skipped until you write them.
7. Make a personal folder that is not committed (e.g. `personal/`): approved plans (`personal/plans/<id>-plan.md`, read by
   the close-out audit), `pas_edit.py` specs, the open-issues list, log copies. Put personal settings (initials for comment
   signatures, this folder's path) in `CLAUDE.local.md`.
8. Add to `.gitignore`: `__pycache__/`, `build/out/`, `build/log/last.log`, `build/old/`, `build/old_source/`,
   `CLAUDE.local.md`, `.claude/settings.local.json` and the personal folder. (Untracked files also show up in the change
   map of `tools/diff_routines.py`.)
9. Line endings: copy `examples/gitattributes` to the project root as `.gitattributes` (only after the binary DFM check
   above). Delphi sources are then stored with LF and always checked out with CRLF, whatever each machine's
   `core.autocrlf` says. In an existing repository run `git add --renormalize .` once and commit it on its own (it may touch
   many files; tell the team first). `pascal_check.py` is still needed: a bare LF written into a working file stays on disk
   until the next commit, and the compiler and IDE read the working file.
10. Give Claude a read-only database user (`examples/readonly-user.postgresql.sql`; other databases under *Databases*) and
    list the users with write access in `write_db_users`.
11. Start a new Claude Code session and check the hooks: ask Claude to run `sed -i "s/a/b/" <some unit>.pas` — it must be
    refused. Then ask it to start the `scope-counter` agent with the task "run `echo $(git log --oneline -1)` once and
    report the exact output or error". The agent must report the hook's refusal ("Read-only agent 'scope-counter':
    command substitution ..."), and the same command run by Claude itself must pass. Use a command that only reads: the
    agent's own instructions forbid writing, so with `touch` it refuses before the hook is ever asked and the test proves
    nothing. If the agent prints the commit line, your Claude Code does not send `agent_type` to hooks (measured present
    in 2.1.332) and only the `git status` / plan hash check in the skills remains. On Windows, finally ask Claude whether it
    has a PowerShell tool: with the deny rule it must say no (a bare tool name in `deny` removes the tool from the
    session, so nothing can be tried with it). If you allowed PowerShell, ask for `'x' | Set-Content probe.pas` instead:
    the hook must refuse it. Repeat these tests after updating Claude Code or
    Python, and after editing `.claude/settings.json` or `.claude/claude-delphi.json`.

`pas_edit.py`, `diff_routines.py` and `closeout_check.py` find `.claude/claude-delphi.json` through `$CLAUDE_PROJECT_DIR`, else by walking up
from the current folder; `pas_callers.py`, the DFM tools and `dfm_text_check.py` take `--root` (default: the current
folder), so run them from the project root.

| Setting in `claude-delphi.json` | Meaning |
|---|---|
| `source_encoding`, `pascal_extensions`, `protected_extensions` | code page and file types the hooks and tools treat as Pascal / protect from `sed -i` and redirection |
| `write_db_users` | database users with write access; a command connecting with one of them is refused |
| `scripts_dir` | where one-off scripts are written (Write) and run by path, instead of inline Python |
| `forbidden_patterns` | project-specific patterns reported when a changed Pascal file gains them, e.g. `{"pattern": "BoolToStr\\s*\\([^)]*,\\s*True\\s*\\)", "message": "use BoolToStr(x)"}`; empty by default |
| `signature_pattern`, `date_format` | comment signature check (see *Localization*); empty pattern = off |
| `measure_marker` | the marker of temporary measurement lines; read by `/triage` and `closeout_check.py` (reports leftover lines); no hook reads it |
| `dead_code_marker` | the dead-code marker named in your `CLAUDE.md`; only a convention for Claude and your team — no skill, hook or tool reads it |
| `forbid_inline_python`, `forbid_gh_write` | turn the inline-Python and GitHub-CLI-write rules off (default on) |
| `warn_binary_dfm` | the SessionStart binary DFM warning (default on) |
| `build_log` | the log `build.bat` writes, relative to the project root (default `build/log/last.log`); `closeout_check.py` checks it is newer than the last change |
| `readonly_agents` | sub-agents whose Bash commands get `command_guard.py` rule 6 (no command substitution, redirection, writing programs or options; a trip wire, not a security boundary); default the three review agents. Keep it equal to the names in `.claude/agents/` (a test checks it) |

## Tests

```
python -m unittest discover -s tests -v
```

Standard library only (no pytest needed); `git` must be on the path. The tests build their Pascal samples at run time and
set their own Git options, so code page and line-ending checks do not depend on how Git checked the repository out. CI runs
them on Windows and Ubuntu (`.github/workflows/tests.yml`).

## Localization

Everything Claude reads (skills, agents, hook messages) is written in English and **is not translated**: Claude follows
English instructions equally well in any language, and translated copies of instructions drift apart. What a local team
needs to adjust is configuration, not text:

| What | Where |
|---|---|
| Language of answers and reports | one line in `CLAUDE.md`: "Communicate with the developer in <language>." |
| Source code page | `source_encoding` in `claude-delphi.json`: `cp1252` (Western Europe), `cp1250` (Central Europe), `cp1251` (Cyrillic), `cp1254` (Turkish), `cp1253` (Greek) ... — single-byte code pages; multi-byte ones (e.g. `cp932` Japanese) are not tested and `pas_callers.py` assumes single-byte |
| Date format of comment signatures | `date_format` (strftime, e.g. `%d.%m.%Y`, `%Y-%m-%d`) and `signature_pattern` (`{date}` placeholder; empty = check off) |
| Markers in code | `measure_marker` (default `X-MEASURE`; read by `/triage` and `closeout_check.py`) and `dead_code_marker` (default `DEAD-CODE`; named in your `CLAUDE.md` only). Set them to what your code really uses: a marker that differs from the code makes `closeout_check.py` miss leftover lines |
| Localized compiler / MSBuild output | nothing to do: `build/summary.py` classifies messages by code (`E`, `F`, `W`, `H`, `MSB`), not by the localized word. Take a new baseline after changing the IDE language. |
| Non-ASCII characters in DFMs | text DFMs store them as `#nnn` escapes of the configured code page; tools read DFMs as Latin-1 and only compare ASCII property names; `pas_edit.py` refuses to write non-ASCII characters into a DFM. |

Human-facing documents (the README, `docs/`) are written in English; translations live under `docs/<language>/` (Turkish
is included). In a translation, the English version prevails in case of conflict. Translations are welcome as
contributions.

## Databases

The package does not depend on a particular database:

| Part | Database dependency |
|---|---|
| `pascal_check.py`, `session_check.py`, `build/`, DFM tools, skills, agents | none |
| `command_guard.py` write-access user rule | none — catches the user name in `psql`, `sqlcmd`, `mysql` / `mariadb`, Firebird `isql` options, the usual environment variables (`PGUSER`, `MYSQL_USER`, `ISC_USER`, `SQLCMDUSER`), connection strings (`User ID=`, `UID=`, `user=`) and URLs (`name:pw@host`) |
| `tools/pg_fingerprint.py` | **PostgreSQL** (`to_jsonb`, `md5`, `information_schema`, `psql`; `public` schema) — an example; for another database, port the idea: per row, an id plus a hash of the content without the id |
| `examples/readonly-user.postgresql.sql` | **PostgreSQL** — on other databases: SQL Server `db_datareader` role, MySQL / MariaDB `GRANT SELECT`, Firebird `GRANT SELECT` per table / a read-only role |
| Diagnostic hints in `docs/` | PostgreSQL examples, each with equivalents for SQL Server, MySQL / MariaDB and Firebird |

Whatever the database, give Claude a **read-only user** and list the users with write access in `write_db_users`.

## Limits

- Written and used on Windows + Git Bash.
- The build check was tested on Delphi 13 / Win32 only. It needs a `.dproj` project (Delphi 2007 or later); older
  projects (`.dof` / `.cfg`) must call `dcc32` directly. For another Delphi version set `DELPHI_RSVARS`
  (e.g. 12 Athens `Studio\23.0`, 11 Alexandria `Studio\22.0`).
- After upgrading Delphi, take a new baseline on the first build (`build.bat baseline`): a new compiler brings new warnings
  and changed message texts.
- Not verified: whether Delphi Community Edition licenses the command-line compiler. Without it `build.bat` does not work;
  the hooks and tools still do.
- `pg_fingerprint.py` and the read-only user script are PostgreSQL examples (see *Databases*).
- Binary DFMs are detected and reported, not read or converted; convert them to text first (see above).
- `pascal_check.py` catches a file saved entirely as UTF-8, not a few UTF-8 lines added to an ANSI file.
- `pas_edit.py` does not remember applied specs: applying the same "additions only" spec twice adds the lines twice.
- `pascal_check.py`'s built-in `date_format` default is `%d.%m.%Y`; the example settings use `%Y-%m-%d`. Set it explicitly.

**What the safety parts do not cover** (from an independent review; what it found and could be fixed is fixed):
- `command_guard.py` is a set of patterns on the command text — a trip wire against habit, for the main session too, not
  only for the review agents. It does not catch: programs that write by themselves (`cp`, `mv`, `dos2unix`,
  `iconv -o`, `git checkout -- file`, a script file), a nested shell (`cmd /c "..."`, `powershell -Command`), inline
  code of other interpreters, targets held in variables.
- The database rule sees a user name only when the command writes it. Connections with implicit credentials (Windows
  authentication `sqlcmd -E`, the OS user name, `PGUSER` already set, `.pgpass`, a service file, a connection string
  inside a script) pass, and SQL text is never inspected. The boundary is a read-only database user and an environment
  that holds no write credentials.
- If `python` is not on the path or a hook times out, Claude Code may run the command unchecked (not verified here).
  Repeat the smoke tests of step 11 after updating Python or Claude Code.
- `pascal_check.py` reports after the write (PostToolUse); it does not prevent it. After a Bash command it sees the
  Pascal files `git status` lists that changed in the last 10 minutes: ignored files, files outside the repository and
  files with a preserved time stamp are not checked. In a repository that stores LF and converts nothing, the committed
  version counts as CRLF, so a file whose working copy is LF is reported as a whole after Bash (Write / Edit compare
  with the file as it was right before).
- "Git is read-only" is a list of command prefixes denied for the Bash tool in `settings.json`, not a mechanism:
  sub-commands not on the list are not refused.
- The review agents cannot use Write / Edit (their `tools` line, checked by a test). Their Bash commands are limited by
  rule 6 only while Claude Code sends `agent_type` to hooks (seen in 2.1.332; not a documented guarantee — the smoke test
  shows it), and rule 6 does not stop a database client: the read-only user does.
- The skills are instructions. Round limits, "no file changes during the audit", what the agents are told and the
  numbers in the review log depend on the model following them. `closeout_check.py` checks that the review log is well
  formed and has a close-out row dated today (a job closed after midnight needs a new row), and that the build log is
  newer than the sources — not that the audit happened or that the build succeeded.

**What the tools do not see:**
- `pascal_lex.py` is not a parser: include files are not expanded, only the first `{$IF}` branch gives routine
  boundaries, local types inside a routine are skipped by a depth count, multi-line `'''` strings and a body in an
  include file raise ParseError.
- `pas_callers.py` searches by name, without type information, in `--root` and the `.dpr` units; other projects,
  packages and a search path outside the root are not searched. It gives "NO VERDICT" instead of "dead" when it knows
  it cannot tell (see the tool's help); a "dead" verdict is still evidence to check, not proof.
- `diff_routines.py --plan` gives a plan status to routines and DFM objects. Changes at unit level (uses, constants,
  types, class declarations) and in non-Pascal files (`.sql`, `.dproj`, `.rc`) get none; only the Scope list ("named
  but not changed") and the close-out agent cover them.
- `dfm_field_check.py` checks only bindings whose DataSource it can resolve to a dataset with persistent fields, and says
  how many it skipped: in a real 700-unit project 1,716 bound controls were skipped against 2,419 checked.
- One project per repository root is assumed (one `.dpr`, one `.dproj`, sources under the root). `build.bat` builds one
  `.dproj`; project groups and package output folders (`.bpl` / `.dcp`) are not redirected (not verified on a package).
- Source code pages: one single-byte code page, or UTF-8, for the whole project. Mixed projects, UTF-16 sources and
  multi-byte ANSI pages (e.g. cp932, where a trail byte can be `{` or `}`) are not supported by the lexer or the tools.
- The SessionStart check runs on a new session only (not on resume) and looks at `.dfm` only, not at binary `.fmx` /
  `.lfm`.

## Contributing and license

See [CONTRIBUTING.md](../CONTRIBUTING.md): new pitfalls, mistake log items, translations and reports from other environments
are welcome. Changes: [CHANGELOG.md](../CHANGELOG.md). License: [MIT](../LICENSE).
