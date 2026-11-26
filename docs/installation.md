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
every session if a binary DFM has appeared, and Claude tells you in its first answer; `pas_edit.py` refuses to edit one;
`pascal_check.py` reports one among changed files.

## Installation

All paths below are relative to the project root (the folder of your `.dpr`, which must be a Git repository).

1. Copy `hooks/*.py` to your project's `.claude/hooks/` folder and `tools/` to a `tools/` folder in the project
   (`pas_edit.py`, `pas_callers.py`, `diff_routines.py`, `dfm_text_check.py` and `pascal_lex.py` must stay together; the hook
   messages refer to `tools/pas_edit.py` and `tools/dfm_text_check.py`).
2. Copy `examples/settings.json` to `.claude/settings.json` (merge if you have one). It wires the three hooks:
   `session_check.py` (SessionStart), `command_guard.py` (PreToolUse) and `pascal_check.py` (PostToolUse). `python` must be on
   the path.
3. Copy `examples/claude-delphi.json` to `.claude/claude-delphi.json` and adjust it (table below and *Localization*).
4. Copy `.claude/skills/` and `.claude/agents/` into your project's `.claude/` folder.
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
    refused.

`pas_edit.py` and `diff_routines.py` find `.claude/claude-delphi.json` through `$CLAUDE_PROJECT_DIR`, else by walking up
from the current folder; `pas_callers.py`, the DFM tools and `dfm_text_check.py` take `--root` (default: the current
folder), so run them from the project root.

| Setting in `claude-delphi.json` | Meaning |
|---|---|
| `source_encoding`, `pascal_extensions`, `protected_extensions` | code page and file types the hooks and tools treat as Pascal / protect from `sed -i` and redirection |
| `write_db_users` | database users with write access; a command connecting with one of them is refused |
| `scripts_dir` | where one-off scripts are written (Write) and run by path, instead of inline Python |
| `forbidden_patterns` | project-specific patterns reported when a changed Pascal file gains them, e.g. `{"pattern": "BoolToStr\\s*\\([^)]*,\\s*True\\s*\\)", "message": "use BoolToStr(x)"}`; empty by default |
| `signature_pattern`, `date_format` | comment signature check (see *Localization*); empty pattern = off |
| `measure_marker`, `dead_code_marker` | markers the skills and your `CLAUDE.md` use; no hook reads them |
| `forbid_inline_python`, `forbid_gh_write` | turn the inline-Python and GitHub-CLI-write rules off (default on) |
| `warn_binary_dfm` | the SessionStart binary DFM warning (default on) |

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
| Markers in code | `measure_marker` (default `X-MEASURE`) and `dead_code_marker` (default `DEAD-CODE`); read by the skills and named in your `CLAUDE.md`, not by the hooks |
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

## Contributing and license

See [CONTRIBUTING.md](../CONTRIBUTING.md): new pitfalls, mistake log items, translations and reports from other environments
are welcome. Changes: [CHANGELOG.md](../CHANGELOG.md). License: [MIT](../LICENSE).
