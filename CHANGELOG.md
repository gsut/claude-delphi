# Changelog

## v0.3.0 — 26.11.2026

The project's goal is now stated at the top of the README: **correctness of the work, not saving tokens.** This release
adds an independent audit at close-out and comes out of the first monthly review of the mistake log and two independent
audits of the package itself.

**Close-out audit (new)**
- `tools/diff_routines.py`: change map — every diff hunk mapped to its routine (Pascal) or object chain (DFM); names
  missing from the plan marked "NOT IN PLAN"; working tree, `--commit` or `--rev A..B`; non-ASCII file names. 11 tests.
- `closeout-auditor` agent and `/close-out` step 2b: an agent that did not do the work compares the approved plan with the
  diff (plan carried out? anything touched outside it? anything broken?) before the commit; its findings are verified by
  hand. In the project this comes from, it found six real bugs in one fifteen-file change before the commit.
- `examples/CLAUDE.md`: the approved plan is written to a file before coding; "correctness over token savings" rule.

**Hooks**
- `command_guard.py` rule 5: no GitHub CLI command that writes to GitHub (creating / editing / deleting releases, PRs,
  issues, repos, workflow runs, secrets; `gh api` with a non-GET method or fields). gh stays usable for reading (view,
  list, `gh api` GET). Catches `gh.exe` called by full path too. Setting `forbid_gh_write` (default true). Tests added.
- `examples/settings.json`: matching `Bash(gh … *)` deny rules as the first layer.

**Tools**
- `pas_edit.py` and `diff_routines.py` find the project root by walking up to `.claude/claude-delphi.json` when
  `$CLAUDE_PROJECT_DIR` is not set (from a subfolder the settings were silently ignored). Test added.
- `dfm_field_check.py` exits with 1 when a field is missing; `pg_fingerprint.py` says clearly when `psql` is not found;
  `build/summary.py` accepts only `baseline` (the undocumented `taban` is gone).

**Mistake log and pitfalls** (English and Turkish)
- First monthly review: [10] split into [10] "search the whole source before generalising or counting" and new [20]
  "before removing / narrowing a call, list what the old call did" — a table in the plan, asked for by `/triage`,
  `/multi-review`, `devils-advocate` and checked at `/close-out`. [17] points to the new pitfall §26; [18] adds "read the
  developer's on-disk version before rewriting". The AI only proposes deleting an item or loosening a check.
- [5] and `scope-counter`: `sort | uniq -d` must print nothing (it does not remove duplicates).
- Pitfall §26: nested `{ }` comments, E2555, UniDAC `DefaultValues` + `RequiredFields`. Now 20 starter items, 26 pitfalls.

**Installation and documents**
- README (English and Turkish): Installation rewritten — project-root paths, `build\` at the root, copy
  `docs/mistake-log.md` and `docs/delphi-pitfalls.md`, a personal folder for plans and specs, `.gitignore` lines, a
  read-only database user, a hook check after install; a table of every `claude-delphi.json` key; known limits (mixed
  UTF-8 lines in an ANSI file, a re-applied "additions only" spec, `date_format` default); `cp932` marked untested.
- `examples/claude-delphi.json`: `forbidden_patterns` is empty (the `BoolToStr` rule was project-specific; it is an
  example in the README now). `examples/CLAUDE.md`: GitHub CLI read-only rule; markers named with their settings.
- `docs/build-baseline.md`: old source is extracted with `git archive | tar` (the `git show … > Unit.pas` recipe was refused
  by `command_guard.py`).
- Smaller fixes: case study table points to [1] instead of [4]; two Turkish pitfall wordings; Turkish README structure;
  `pg_fingerprint` public schema only; docstrings of `pas_edit.py` / `pascal_lex.py`.

**Independence check:** a fresh install from the README into a throwaway project, with no access to the original project,
ran the tests, tools and hooks; no leak of or dependency on the original project was found.

**Tests:** 47 (was 32 at v0.1.0).

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
