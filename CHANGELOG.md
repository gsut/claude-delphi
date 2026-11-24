# Changelog

## Unreleased

- `command_guard.py` rule 5: no GitHub CLI command that writes to GitHub (creating / editing / deleting releases, PRs,
  issues, repos, workflow runs, secrets; `gh api` with a non-GET method or fields). gh stays usable for reading (view, list,
  `gh api` GET). Catches `gh.exe` called by full path too. Setting `forbid_gh_write` (default true). Tests added.
- `examples/settings.json`: matching `Bash(gh … *)` deny rules as the first layer.

## v0.2.0 — 24.11.2026

**Tools**
- `pas_edit.py --reverse` (new): undoes a spec that was applied — each `new` is replaced by its `old`, last edit first;
  `additions_only` is ignored. Removes temporary measurement lines with the same spec that added them.
  Test `test_reverse_restores_the_file`.
- `pas_edit.py` (fix): in DFM files only the **inserted** text must be ASCII. IDE-saved DFMs in UTF-8 with BOM already contain
  non-ASCII characters, and the whole-file check refused every edit to them.
- `pas_edit.py` (fix): a `routine`-scoped anchor that ends with the routine's final `end;` and its line break is now found;
  the routine range used to stop at the `;`.

**Docs** (English and Turkish)
- Mistake log [1]: a command written into a document is tried exactly as written there (redirection and pipe included);
  on Windows, Python writes redirected output in the console code page, not UTF-8.
- Mistake log [16]: a cell lock given in a grid's `OnGetCellParams` (`Params.ReadOnly`) must also be given when
  `EditMode = True` — EhLib asks for edit permission that way (`TAxisBarEh.CanModify`).
- Pitfalls 23–25: a dataset without a master link refreshed inside a loop fetches the whole table each time; walking tree
  nodes by selection fires the change event for every node; over a network, count server round trips
  (`pg_stat_statements`), not server time.

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
