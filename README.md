# claude-delphi

Hooks, skills, agents, small tools and a working method for using [Claude Code](https://claude.com/claude-code) safely on a
legacy **Delphi VCL + database** code base.

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
| Repeats the same mistake session after session; `CLAUDE.md` keeps growing | `docs/mistake-log.md`: short, every item is a **rule + a check** |

## Contents

```
hooks/
  command_guard.py         PreToolUse (Bash): inline Python, sed -i / redirection into protected files, write-access DB users
  pascal_check.py          PostToolUse: new bare LF, wrong encoding, project-specific forbidden patterns, double signatures
build/
  build.bat, summary.py    command-line build + diff against the warning baseline
tools/
  pas_edit.py              safe replacement in Pascal / DFM files: keeps code page + CRLF, anchor must occur exactly once,
                           optionally only inside a named routine, optional "additions only" check
  pas_callers.py           every reference to a routine: code (with enclosing routine), other {$IF} branches, DFM
                           bindings, name strings, comments; a dead-code verdict with evidence
  pascal_lex.py            small Pascal lexer / routine finder used by the tools (nested routines, {$IF} branches)
  dfm_field_check.py       does the field of each control bound to a DataSource exist in the dataset
  dfm_field_usage.py       which DFM controls are bound to the given field names
  pg_fingerprint.py        fingerprint of one record's rows across all tables, before / after diff
.claude/
  skills/                  build-check, triage, review, multi-review, close-out
  agents/                  scope-counter, devils-advocate (for multi-review)
docs/
  mistake-log.md           method, template and 19 starter items
  delphi-pitfalls.md       22 recurring Delphi + database pitfalls
  build-baseline.md        details and pitfalls of the build check
  case-study.md            a real case told step by step: empty twin rows, from symptom to root cause
  tr/                      Turkish translations
tests/                     unittest suite for hooks, build summary and tools
examples/
  CLAUDE.md                team rules template
  settings.json            hook wiring + permissions that block Git write commands
  claude-delphi.json       hook settings (code page, extensions, forbidden patterns, DB users, markers)
  readonly-user.postgresql.sql   read-only database user for Claude (PostgreSQL)
```

## Requirements

No pip packages: everything uses the Python standard library.

| Requirement | Needed by | Notes |
|---|---|---|
| **Python 3.9+**, on the path as `python` | hooks, tools, `summary.py`, tests | Tested locally on 3.13; CI is set up for 3.9 and 3.13. `settings.json` calls `python -I …`; if the command is `python3` on Linux / macOS, change it there. |
| **Git**, on the path | `pascal_check.py` (tells new violations from old ones), tests | The project must be a Git repository. |
| **Claude Code**, a version with skills and sub-agents | hooks, `.claude/skills/`, `.claude/agents/` | `/multi-review` starts two sub-agents in parallel. |
| **Delphi 2007 or later** (`.dproj`, `msbuild`, `rsvars.bat`) | `build/` only | The licence must include the command-line compiler; Community Edition not verified. |
| **psql** (PostgreSQL client) + a read-only user | `pg_fingerprint.py` only | Not used with other databases. |
| **Windows + Git Bash** | recommended environment | Everything was written and used there; `build.bat` is Windows-only. Hooks and tools should run on Linux (CI includes Ubuntu) but were not tried in a real Linux Delphi setup. |

## Installation

1. Copy `hooks/*.py` to your project's `.claude/hooks/` folder and `tools/` to a `tools/` folder in the project
   (`pas_edit.py`, `pas_callers.py` and `pascal_lex.py` must stay together; the hook messages refer to `tools/pas_edit.py`).
2. Copy `examples/settings.json` to `.claude/settings.json` (merge if you have one). `python` must be on the path.
3. Copy `examples/claude-delphi.json` to `.claude/claude-delphi.json` and adjust it (see *Localization* below).
4. Copy `.claude/skills/` and `.claude/agents/` into your project's `.claude/` folder.
5. Put `build/` in a folder of your project; set `DELPHI_RSVARS`, `DELPHI_DPROJ`, `DELPHI_CONFIG`, `DELPHI_PLATFORM` in
   `build.bat` (or as environment variables). Keep the `.bat` file CRLF. First run: `build.bat baseline`.
6. Copy `examples/CLAUDE.md` to the project root and fill in the bracketed parts. Make `docs/mistake-log.md` the start of
   your own log and load it from `CLAUDE.md` with `@`.

The hooks use Git to tell new violations from old ones; the project must be a Git repository.

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
| Source code page | `source_encoding` in `claude-delphi.json`: `cp1252` (Western Europe), `cp1250` (Central Europe), `cp1251` (Cyrillic), `cp1254` (Turkish), `cp1253` (Greek), `cp932` (Japanese) ... |
| Date format of comment signatures | `date_format` (strftime, e.g. `%d.%m.%Y`, `%Y-%m-%d`) and `signature_pattern` (`{date}` placeholder; empty = check off) |
| Markers in code | `measure_marker` (default `X-MEASURE`) and `dead_code_marker` (default `DEAD-CODE`) |
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

To see it at work on a real bug, read the [case study](docs/case-study.md).

- **Hypothesis first, then approval, then the fix.** The AI says "the cause is X, my evidence is Y, this measurement tells
  them apart" and stops.
- **Measure first.** Temporary measurement lines carry a marker and are removed when the work is done.
- **Surgical changes, but copies are merged.** Adjacent code is not touched; instead of adding the same fix to every copy of
  a routine, the copies are merged into a shared routine.
- **Dead code is not deleted but marked with evidence** (`// DEAD-CODE: <evidence>`); deletion is a separate decision.
- **Git and the database are read-only for the AI.** Commits, deployment and data-changing scripts belong to the developer.
- **A blind second reading.** For a structural change, an independent agent gets only what will change, not the plan's
  conclusion; its findings are verified in the source before being presented to the developer as facts.
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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md): new pitfalls, mistake log items, translations and reports from other environments
are welcome. Changes: [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE)
