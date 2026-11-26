# claude-delphi

[![tests](https://github.com/gsut/claude-delphi/actions/workflows/tests.yml/badge.svg)](https://github.com/gsut/claude-delphi/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Hooks, skills, agents, small tools and a working method for getting **correct** work out of
[Claude Code](https://claude.com/claude-code) on a legacy **Delphi VCL + database** code base.

> **The goal is correctness, not saving tokens.** Every part of this repository exists to make the AI's work right: the
> diagnosis, the change and the report. Many steps cost tokens and time on purpose — a measurement before a fix, an
> independent agent that reads the change without being told the plan's conclusion, a count repeated with a second method,
> an audit at close-out even after a one-line change. On a legacy code base the expensive thing is not a long session; it
> is a wrong fix that compiles, looks plausible and reaches a customer's data. When a choice is between a cheaper session
> and a more reliable result, this repository chooses the reliable result. A step is dropped only when measurement shows
> it does not catch anything, never just to save tokens.

Collected over months of daily use on a real project (hundreds of units, thousands of compiler warnings, ANSI code page
sources, a multi-tenant database). Everything specific to that project has been removed; what remains is a core you can
adapt to other Delphi projects.

> **Status:** shared as examples and a method; no support is offered. Claude Code's hook / skill format may change, so the
> mechanics may age — the method will not.

Türkçe: [docs/tr/README.md](docs/tr/README.md)

## What it solves

The places where an AI most often does damage or wastes time in a legacy Delphi project:

| Problem | Answer in this repository |
|---|---|
| Saves a `cp1252` / `cp1254` source as UTF-8, turns CRLF into LF | `hooks/pascal_check.py` (reports only **new** violations, compared with Git) |
| Breaks files with `sed -i`, `>` redirection or inline scripts | `hooks/command_guard.py` (refuses before the command runs) and `tools/pas_edit.py` (the safe way to do it) |
| Connects to the database with a user that can write | `hooks/command_guard.py` + a read-only user rule |
| Hands over a change without compiling; cannot see a new warning among thousands of old ones | `build/build.bat` + `summary.py`: **0 errors and 0 new warnings vs baseline**, language independent |
| Cannot see DFM field bindings (removes a field and breaks a screen, calls bound code "dead") | `tools/dfm_field_check.py`, `tools/dfm_field_usage.py` |
| Calls code "dead" after a grep that missed a nested routine, a DFM event or a commented-out call | `tools/pas_callers.py` (references grouped by kind, with the enclosing routine) |
| Guesses from code "what else did this operation touch?" | `tools/pg_fingerprint.py` (before / after fingerprint; PostgreSQL) |
| Builds a nice story from code and fixes without measuring | `/triage` skill: hypothesis + evidence + a measurement that tells them apart, **no code** |
| Gets "approval" from a sub-agent that just confirms its own plan | `/review`, `/multi-review`: the agent gets only the change, not the conclusion; scope counted on four axes |
| Calls a job "done" when the plan was only partly applied, or something outside it was touched | `/close-out` step 2b: `tools/diff_routines.py` maps the diff to routines / DFM objects against the plan, then the `closeout-auditor` agent checks plan ↔ diff and looks for breakage, before the commit |
| Repeats the same mistake session after session; `CLAUDE.md` keeps growing | `docs/mistake-log.md`: short, every item is a **rule + a check** |

## Contents

```
hooks/
  command_guard.py         PreToolUse (Bash): inline Python, sed -i / redirection into protected files, write-access DB users,
                           GitHub CLI commands that write (gh stays read-only)
  pascal_check.py          PostToolUse: new bare LF, wrong encoding, project-specific forbidden patterns, double signatures
build/
  build.bat, summary.py    command-line build + diff against the warning baseline
tools/
  pas_edit.py              safe replacement in Pascal / DFM files: keeps code page + CRLF, anchor must occur exactly once,
                           optionally only inside a named routine, optional "additions only" check; --reverse undoes
                           an applied spec (e.g. removes temporary measurement lines)
  pas_callers.py           every reference to a routine: code (with enclosing routine), other {$IF} branches, DFM
                           bindings, name strings, comments; a dead-code verdict with evidence
  pascal_lex.py            small Pascal lexer / routine finder used by the tools (nested routines, {$IF} branches)
  dfm_field_check.py       does the field of each control bound to a DataSource exist in the dataset
  dfm_field_usage.py       which DFM controls are bound to the given field names
  pg_fingerprint.py        fingerprint of one record's rows across all tables (public schema), before / after diff
  diff_routines.py         change map: every diff hunk mapped to its routine (Pascal) or object chain (DFM), names
                           missing from the plan marked; working tree, one commit or a range
.claude/
  skills/                  build-check, triage, review, multi-review, close-out
  agents/                  scope-counter, devils-advocate (for multi-review), closeout-auditor (for close-out)
docs/
  mistake-log.md           method, template and 20 starter items
  delphi-pitfalls.md       26 recurring Delphi + database pitfalls
  build-baseline.md        details and pitfalls of the build check
  case-study.md            a real case told step by step: empty twin rows, from symptom to root cause
  tr/                      Turkish translations
tests/                     unittest suite for hooks, build summary and tools
examples/
  CLAUDE.md                team rules template
  settings.json            hook wiring + permissions that block Git write commands
  claude-delphi.json       settings read by hooks, tools and skills (code page, extensions, forbidden patterns, DB users, markers)
  readonly-user.postgresql.sql   read-only database user for Claude (PostgreSQL)
```

## Requirements

No pip packages: everything uses the Python standard library.

| Requirement | Needed by | Notes |
|---|---|---|
| **Python 3.11+**, on the path as `python` | hooks, tools, `summary.py`, tests | CI runs 3.11 and 3.13 on Windows and Ubuntu; older 3.x versions may work but are not tested. `settings.json` calls `python -I …`; if the command is `python3` on Linux / macOS, change it there. |
| **Git**, on the path | `pascal_check.py` (tells new violations from old ones), tests | The project must be a Git repository. |
| **Claude Code**, a version with skills and sub-agents | hooks, `.claude/skills/`, `.claude/agents/` | `/multi-review` starts two sub-agents in parallel. |
| **Delphi 2007 or later** (`.dproj`, `msbuild`, `rsvars.bat`) | `build/` only | The licence must include the command-line compiler; Community Edition not verified. |
| **psql** (PostgreSQL client) + a read-only user | `pg_fingerprint.py` only | Not used with other databases. |
| **Windows + Git Bash** | recommended environment | Everything was written and used there; `build.bat` is Windows-only. Hooks and tools should run on Linux (CI includes Ubuntu) but were not tried in a real Linux Delphi setup. |

## Installation

All paths below are relative to the project root (the folder of your `.dpr`, which must be a Git repository).

1. Copy `hooks/*.py` to your project's `.claude/hooks/` folder and `tools/` to a `tools/` folder in the project
   (`pas_edit.py`, `pas_callers.py`, `diff_routines.py` and `pascal_lex.py` must stay together; the hook messages refer to `tools/pas_edit.py`).
2. Copy `examples/settings.json` to `.claude/settings.json` (merge if you have one). `python` must be on the path.
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
9. Give Claude a read-only database user (`examples/readonly-user.postgresql.sql`; other databases under *Databases*) and
   list the users with write access in `write_db_users`.
10. Start a new Claude Code session and check the hooks: ask Claude to run `sed -i "s/a/b/" <some unit>.pas` — it must be
    refused.

`pas_edit.py` and `diff_routines.py` find `.claude/claude-delphi.json` through `$CLAUDE_PROJECT_DIR`, else by walking up
from the current folder; `pas_callers.py` and the DFM tools take `--root` (default: the current folder), so run them from the
project root.

| Setting in `claude-delphi.json` | Meaning |
|---|---|
| `source_encoding`, `pascal_extensions`, `protected_extensions` | code page and file types the hooks and tools treat as Pascal / protect from `sed -i` and redirection |
| `write_db_users` | database users with write access; a command connecting with one of them is refused |
| `scripts_dir` | where one-off scripts are written (Write) and run by path, instead of inline Python |
| `forbidden_patterns` | project-specific patterns reported when a changed Pascal file gains them, e.g. `{"pattern": "BoolToStr\\s*\\([^)]*,\\s*True\\s*\\)", "message": "use BoolToStr(x)"}`; empty by default |
| `signature_pattern`, `date_format` | comment signature check (see *Localization*); empty pattern = off |
| `measure_marker`, `dead_code_marker` | markers the skills and your `CLAUDE.md` use; no hook reads them |
| `forbid_inline_python`, `forbid_gh_write` | turn the inline-Python and GitHub-CLI-write rules off (default on) |

## Tests

```
python -m unittest discover -s tests -v
```

Standard library only (no pytest needed); `git` must be on the path. The tests build their Pascal samples at run time, so
code page and CRLF checks do not depend on how Git checked the repository out. CI runs them on Windows and Ubuntu
(`.github/workflows/tests.yml`).

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
| Non-ASCII characters in DFMs | DFMs store them as `#nnn` escapes of the configured code page; tools read DFMs as Latin-1 and only compare ASCII property names; `pas_edit.py` refuses to write non-ASCII characters into a DFM. |

Human-facing documents (this README, `docs/`) are written in English; translations live under `docs/<language>/`
(Turkish is included). In a translation, the English version prevails in case of conflict. Translations are welcome as
contributions.

## Databases

The package does not depend on a particular database:

| Part | Database dependency |
|---|---|
| `pascal_check.py`, `build/`, DFM tools, skills, agents | none |
| `command_guard.py` write-access user rule | none — catches the user name in `psql`, `sqlcmd`, `mysql` / `mariadb`, Firebird `isql` options, the usual environment variables (`PGUSER`, `MYSQL_USER`, `ISC_USER`, `SQLCMDUSER`), connection strings (`User ID=`, `UID=`, `user=`) and URLs (`name:pw@host`) |
| `tools/pg_fingerprint.py` | **PostgreSQL** (`to_jsonb`, `md5`, `information_schema`, `psql`) — an example; for another database, port the idea: per row, an id plus a hash of the content without the id |
| `examples/readonly-user.postgresql.sql` | **PostgreSQL** — on other databases: SQL Server `db_datareader` role, MySQL / MariaDB `GRANT SELECT`, Firebird `GRANT SELECT` per table / a read-only role |
| Diagnostic hints in `docs/` | PostgreSQL examples, each with equivalents for SQL Server, MySQL / MariaDB and Firebird |

Whatever the database, give Claude a **read-only user** and list the users with write access in `write_db_users`.

## The method in short

To see it at work on a real bug, read the [case study](docs/case-study.md) — or the story on Medium:
[The Empty Twin Rows: Using Claude Code on a Legacy Delphi Code Base](https://medium.com/@gokhan.sut_29411/the-empty-twin-rows-using-claude-code-on-a-legacy-delphi-code-base-9d0f7fbd723a).

- **Hypothesis first, then approval, then the fix.** The AI says "the cause is X, my evidence is Y, this measurement tells
  them apart" and stops.
- **Measure first.** Temporary measurement lines carry a marker and are removed when the work is done.
- **Surgical changes, but copies are merged.** Adjacent code is not touched; instead of adding the same fix to every copy of
  a routine, the copies are merged into a shared routine.
- **Dead code is not deleted but marked with evidence** (`// DEAD-CODE: <evidence>`); deletion is a separate decision.
- **Git and the database are read-only for the AI.** Commits, deployment and data-changing scripts belong to the developer.
- **A blind second reading.** For a structural change, an independent agent gets only what will change, not the plan's
  conclusion; its findings are verified in the source before being presented to the developer as facts.
- **An independent audit before the commit.** The approved plan is written to a file before coding; at close-out an agent
  that did not do the work compares it with the diff.
- **At the end of every job:** how it was done, what the actual bug was, what the AI's own mistake was. A repeatable
  mistake goes into the mistake log in the same turn; a mistake a pattern can catch goes into a hook.

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
- The DFM tools read text DFMs (binary DFMs are not supported).
- `pascal_check.py` catches a file saved entirely as UTF-8, not a few UTF-8 lines added to an ANSI file.
- `pas_edit.py` does not remember applied specs: applying the same "additions only" spec twice adds the lines twice.
- `pascal_check.py`'s built-in `date_format` default is `%d.%m.%Y`; the example settings use `%Y-%m-%d`. Set it explicitly.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md): new pitfalls, mistake log items, translations and reports from other environments
are welcome. Changes: [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE)
