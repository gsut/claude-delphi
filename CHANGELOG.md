# Changelog

## v0.1.0 — first public release

Collected from months of daily use of Claude Code on a legacy Delphi VCL + PostgreSQL project, with everything
project-specific removed.

**Hooks**
- `command_guard.py` (PreToolUse, Bash): refuses inline Python, `sed -i` / `perl -i` and shell redirection into protected
  files, and connections as a database user with write access (psql, sqlcmd, mysql / mariadb, Firebird isql, environment
  variables, connection strings, URLs).
- `pascal_check.py` (PostToolUse): reports new bare LFs, files saved as UTF-8 when sources use an ANSI code page,
  project-specific forbidden patterns and double signatures — only violations that are new compared with Git.

**Build check**
- `build/build.bat` + `summary.py`: command-line build with a warning baseline ("0 errors and 0 new warnings"); messages
  are classified by code, so localized Delphi / MSBuild output works.

**Tools**
- `pas_edit.py`: safe replacement in Pascal / DFM files (code page and CRLF kept, anchor exactly once, optional routine
  scope, optional additions-only check, all-or-nothing).
- `pas_callers.py`: every reference to a routine — code (with the enclosing routine), other `{$IF}` branches, DFM bindings,
  name strings, comments — and a dead-code verdict with evidence.
- `pascal_lex.py`: small Object Pascal lexer and routine finder (nested routines, `{$IF}` branches, text after `end.`).
- `dfm_field_check.py`, `dfm_field_usage.py`: DFM field bindings.
- `pg_fingerprint.py`: before / after fingerprint of one record's rows across all tables (PostgreSQL).

**Skills and agents**
- `/build-check`, `/triage`, `/review`, `/multi-review`, `/close-out`; agents `scope-counter`, `devils-advocate`.

**Documents**
- Mistake log method with 19 starter items, 22 Delphi + database pitfalls, build baseline notes, a case study.
- Turkish translations under `docs/tr/`.

**Tests**
- 32 unittest tests (standard library only); CI on Windows and Ubuntu.
