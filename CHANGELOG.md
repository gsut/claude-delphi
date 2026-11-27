# Changelog

## Unreleased

- `pas_callers.py`: `.dpr` unit paths (`U in '..\U.pas'`) are written with `\`; on Linux / macOS that was no separator,
  so units outside `--root` were not seen ("NO VERDICT" missing) and the "[not in .dpr]" marks were wrong. Found by the
  Ubuntu CI run of v0.5.0 (`test_dpr_unit_outside_root`).

## v0.5.0 — 27.11.2026

An independent audit of the whole repository (consistency, limitations, reliability) closed safety gaps in the hooks
(line endings in LF-storing repositories, the PowerShell tool, failing closed), tools that said "OK" when they should not,
and routines the lexer silently dropped. Plans now have a template, reviews a log, and a new `closeout_check.py` checks a
finished job mechanically. Tested on three real tickets in a 700-unit project.

**Independent audit — group A (safety)**: three independent reviews (consistency, limitations, reliability) of the whole
repository; the findings below were reproduced before fixing, and each fix has a test that fails on the previous version.
- `pascal_check.py`, line endings: the baseline was `git show HEAD:` — in a repository that stores LF (the
  `.gitattributes` of the installation guide, `core.autocrlf=true`, or LF stored with nothing converting it, seen in a
  real project) every committed line counted as a bare LF, so new bare LFs were not reported. Now the baseline is a
  snapshot of the file taken in PreToolUse (Write / Edit; "did this tool call add a bare LF?"), else the committed
  version as checked out (`git cat-file --filters`), and a committed version without any CR counts as CRLF.
- `pascal_check.py`, other: non-ASCII paths (`C:\Users\Gökhan\...`) were silently not checked (stdin decoded in the
  console code page); after Bash, files outside the current folder or with an upper-case extension were missed (now the
  whole repository, any case); an invalid `forbidden_patterns` regex crashed the hook and dropped every check (now
  reported, the rest still runs).
- `command_guard.py`: the **PowerShell** tool was not checked at all (and the `Bash(...)` deny rules do not apply to it):
  now rules 1-5 apply to it, plus `Set-Content` / `Add-Content` / `Out-File` / `Tee-Object` / `[IO.File]::Write...` on a
  protected file; a read-only agent may not use it. `examples/settings.json` denies the PowerShell tool and wires the
  hook to it. Passed before, refused now: a quoted redirection target (`> "Unit1.pas"`), `x>Unit1.pas`, `>|`, a second
  `tee` target, `sed` / `perl` by full path or quoted, `perl -0pi`, `python -Ic` / `-uc` / `-c"…"`, `python<<EOF`, a pipe
  into a bare `python`, `pythonw`, `psql -wU user`, `gh -R o/r pr create`, `gh ssh-key add`, `gh pr revert`. Refused
  before, allowed now: `grep 'use sed -i here'`, `perl script.pl -input x.pas`, `gh repo deploy-key list`.
- `command_guard.py` fails closed: hook input that is not a JSON object, and a settings file that exists but cannot be
  read, refuse the command (before: a trailing comma or a BOM in `claude-delphi.json` silently switched the write-user
  rule off). Settings are read with or without a BOM (Notepad, PowerShell 5.1).
- `hooks/hook_common.py` (new): settings and hook input for the three hooks, which each had their own copy of the
  silent fall-back. `session_check.py` announces an unreadable settings file and a binary-DFM scan cut short with
  nothing found (it used to look clean).
- `build/summary.py`: a failed build read as "errors: 0" — `Targets(396,5)` (line and column) and `F1026` were not
  recognised and the exit code was ignored. Now `(line,column)` is accepted, a non-zero exit code without a recognised
  error line counts as an error, localized MSBuild warnings are no longer counted as errors, a baseline is never saved
  from a failed build, blank baseline lines and non-ASCII messages no longer crash it.
- Tests: `run_hook` sends raw UTF-8 as Claude Code does and fails on a hook that exits non-zero or writes to stderr
  (a crashed hook used to pass as "silent = allowed").
- **Group B (tools that said "OK" when they should not):**
  - `pas_callers.py` printed a ready dead-code evidence line for live code. Now: a call inside a parameterless anonymous
    method (`procedure begin … end`) is found (the `begin` was taken for a header name); no verdict ("NO VERDICT" with
    the reasons) when a reference is in a unit the `.dpr` does not list, the routine is declared `override` / `virtual`
    / `dynamic` / `message`, a `.dpr` unit lies outside `--root`, a file could not be parsed, or a DFM is binary (its
    bindings used to be skipped silently); exported routines are listed. Now imports `dfm_text_check`.
  - `diff_routines.py` / `closeout_check.py`: `git diff` now runs with `--no-ext-diff --no-textconv
    --inter-hunk-context=0` (with an external diff tool configured, every change read as "line endings only" and an
    added `CreateForm` as OK; a merged hunk charged an untouched routine). A changed file without hunks says why: binary
    content changed, new empty file, or line endings only. One shared `diff_raw()` for both tools.
  - `diff_routines.py --plan`: a mention qualified with another class (`TFormA.Button1Click`) no longer covers
    `TFormB.Button1Click`; routines of new untracked units (every unit Claude creates) are listed and checked against
    the plan.
  - `closeout_check.py` new-form: a data module / frame registered the IDE way (`{DmMain: TDataModule}`) was a FAIL.
  - `pas_edit.py`: a routine with a forward declaration could not be the `routine` scope (two matches).
- **Group C (lexer):** `pascal_lex.py` silently dropped or cut short routines after a cracker / exception class without
  a body (`TX = class(TBase);`), a generic `<T: record>` constraint, an attribute (`[Test]`), `(*$IFDEF*)` directives,
  `end` used as a name (`Range.End[xlUp]`, asm `@@end`), an inline `var R: record … end`, and nested generic class names.
  Checked on 704 units of a real project before / after: 698 identical, 6 gained routines the old version dropped (the
  cracker class pattern), none lost, no new ParseError.
- **Group D (documents):**
  - README (EN / TR): the workflow had the blind review after the code and said it "audits only the diff"; it reviews the
    plan before any code. `/triage` proposes a measurement (it does not add lines before approval); the tools read plan
    items and scope only. Overclaims corrected: `pascal_check` reports (does not block), the build summary reports (the
    skill makes it the rule), the close-out lists differences (no "1:1"), the test suite is not "full". Badge links
    point to the installation guide.
  - `docs/installation.md` (EN / TR): Limits gets two new parts — what the safety parts do not cover and what the tools
    do not see — from the independent review, minus what groups A–C fixed. `dead_code_marker` is described as a
    convention no skill or tool reads (the guide said the skills read it).
  - Plan template and skills agree: the scope count goes into the Assumptions section in `/review` and `/multi-review`
    step 1, the test steps into the Test steps section in `/close-out` step 5.
  - `dfm_field_check.py` says how many bound controls it did not check (a real project: 1,716 skipped against 2,419
    checked; "0 missing" used to look complete). `--exclude` shown in the usage of the three tools that have it, with one
    default. CONTRIBUTING's Localization link, the rule-6 header (`grep -O`), "every new session".
- `docs/installation.md` (EN / TR): copy all of `hooks/` and the whole `tools/` folder (the tools import each other —
  list given; a selective copy failed with `ModuleNotFoundError` when the tools were moved into a real project); the
  PowerShell deny rule; a third smoke test; repeat the smoke tests after updates.

**Hooks**
- `command_guard.py` rule 6 (new): Bash commands of the read-only review agents (`readonly_agents`, default
  `scope-counter`, `devils-advocate`, `closeout-auditor`; recognised by the hook input's `agent_type`, measured present in
  Claude Code 2.1.332; plugin names `plugin:name` match too). Refused: command substitution (`$( )`, backticks, `<( )`,
  `>( )`, also inside double quotes), any redirection into a file (`2>&1`, `>&2` and `/dev/null` stay allowed), a variable
  assignment in front of a command, programs that write or run others (`rm`, `cp`, `touch`, `tee`, `xargs`, `bash`,
  `awk`, `env`, `source` ...), git subcommands other than reading ones and `-c` / `--output` / `grep -O` /
  `--open-files-in-pager` / `--ext-diff` / `hash-object -w`, `find -delete` / `-exec*` / `-ok*` / `-fprint*` / `-fls`,
  `sed` other than `sed -n <range>p`, `sort -o`, `uniq IN OUT`, `rg --pre`, database client options that write a local
  file (`-o`, `-L`, `--tee`, psql `\o` / `\copy` / `\!`), `python` other than the read-only tools. Unlisted programs are
  allowed, so `cd`, `sort | uniq -d`, `for` loops keep working: a trip wire against habit, not a security boundary.
  `git diff --output=<tracked file>` was shown to overwrite the file; it is among the 69 test cases, most of them taken
  from two independent reviews of the plan.
- `command_guard.py`: if the hook itself fails on a command, the command is now refused instead of passing unchecked.
- Skills: `/review`, `/multi-review` and `/close-out` compare `git hash-object <plan file>` before and after the agent;
  `git status` does not see the ignored personal folder where the plan lives.
- `docs/installation.md` step 11: a second smoke test — `scope-counter` runs `echo $(git log --oneline -1)` and must
  report the hook's refusal, while the same command from the main session passes. A writing command (`touch`) does not
  work as a test: the agent refuses it on its own instructions before the hook is asked (tried).

**Tools**
- `tools/closeout_check.py` (new): the mechanical part of `/close-out` step 2 and the `/build-check` notes in one
  read-only command, instead of hand-run `grep`s. Checks: no measure-marker line left, no untracked `.bak` (ignored ones
  included), no `CreateForm` line added to a `.dpr`, new form units registered in the `.dpr` / `.dproj`, the build log
  newer than every changed source; a changed data module is a NOTE. Exit 1 on any FAIL; `--base REV` for committed work.
  Uses the root, settings and Git helpers of `diff_routines.py` (no copy). New setting `build_log` (default
  `build/log/last.log`). Tests `test_closeout_check.py`.
- `diff_routines.py --plan`: if the plan has the template's section markers, only `plan:items` and `plan:scope` are
  searched. A routine named only in the evidence or among the callers that stay unchanged used to count as "in plan" and
  hid a real "NOT IN PLAN". A plan without markers is searched whole, as before; the header says which.

**After the first real job with the template** (one ticket on a 700-unit project; observations from that session):
- `diff_routines.py --plan`, other direction: every file, routine or DFM object written in backticks in the plan's Scope
  that no change touches is listed at the end ("Named in the plan's Scope but not changed"). Scope lists only what will
  change, so such an entry is a forgotten item, a contingency in the wrong section, or a document still to update. Names
  in new untracked units count as changed. Only for plans with section markers.
- `diff_routines.py --plan`: a comment-only change at unit level right above a routine (a dead-code marker) is checked
  against the plan with that routine's name ("in plan (comment above X)"); it used to show without a plan status.
- Plan template: new `plan:contingency` section for steps carried out only under a condition (the tools do not read it);
  Scope asks for backticks only around files, routines and DFM objects that will change (a backticked table-row name
  gave the first false entry); the Assumptions section also holds your own scope count.
- Review log template and `/review`, `/multi-review`: `scope-counter`'s Findings also count findings in its answers to the
  extra questions. `closeout-auditor` knows `plan:contingency` and the not-changed list.
- `/close-out` 2b: no file changes while the audit runs (the session had updated documents in parallel and the auditor
  saw the tree change under it); documents are updated in step 4, after the audit.
- Mistake log [16] (EN / TR): a new check — when clearing / changing a component property or wiring an event, look in
  the component source whether the part's visibility depends on it (EhLib `EditButton` / `DefaultVisible`); a wired button
  goes into the test instructions only after it was seen on screen.
- Second job (HP-255; its review found a critical gap: a protected file was writable through an older path):
  - `diff_routines.py`: a class named in Scope counts as changed when one of its methods changed (a method added to the
    class declaration maps to unit level — false "not changed" entry); comment lines above a routine are matched line by
    line, not per hunk (an explanation added in the same hunk as its new routine was not matched); a unit-level change of
    blank lines only gets no plan status. Both false alarms gone on the real commit.
  - Review log template: "Accepted" = opened and found real, whatever became of it; the split (plan / test / question)
    goes into Note (a devil's advocate at 7 of 7 looked like 7 plan changes; two were questions).
  - `/triage` step 7: commit the previous job first when the same file is touched (the map compares with HEAD).
  - `/review`, `/multi-review` step 4: if the plan changes, read its [20] table again (it went from "none" to three rows
    after the review).
  - Mistake log [9] (EN / TR): a change that opens a new write path gets a reachability row for read-only / protected
    modes — the general form of that job's critical finding.
- Third job (HP-256, a small column-header change whose review still found a wrong period name affecting three screens):
  - `diff_routines.py`: added comment lines at unit level now belong to whatever the next code line declares — a routine
    header or a declaration in the interface / a class — instead of the next routine body further down the file. A
    comment above an interface declaration had been charged to an unrelated routine and reported NOT IN PLAN; the
    three false-alarm kinds of the three jobs (class declaration, explanation above a new routine, interface
    declaration comment) had this one root. Comments followed by other code belong to nothing. Checked on all three
    real commits: no false NOT IN PLAN left.
  - Plan template: "Deviations from the request (approved by …)" line in the Request section (both later jobs had put
    them at the end of the request text by hand).
- Kept as they were (worked in the trial): the [20] table found a difference the conversation had missed (the plan item
  it produced was then shown unnecessary by both review agents independently); the plan hash check; the "Not opened"
  column, whose counting led to two unopened findings being opened; `closeout_check.py` with no false alarm.

**Plan file template (new)** — `.claude/templates/plan.md`: sections gathered from what the skills already asked for
(request, hypothesis and evidence, numbered plan items, scope, other callers not changed, the mistake log [20] table,
commit point, assumptions, test steps). Language-independent `<!-- plan:... -->` markers; headings and text in the
developer's language. `/triage` step 7 (new) writes the plan file from it after approval; `/multi-review` writes the
assumptions into it and hands the [20] section to `devils-advocate`; `closeout-auditor` knows the sections. No separate
"plan check" tool: a heading-presence check would prove nothing.

**Review log (new)** — replaces the optional measurement tables of `/multi-review` step 5 and `/close-out` 2b-4.
- `.claude/templates/reviews.md`: one row per agent per round next to the plan (`<id>-reviews.md`): date, step, round,
  agent, findings, accepted, accepted critical, not opened by the session, note. Written by `/review`, `/multi-review` and
  `/close-out` after the session has verified the findings; `/triage` step 5 adds an `after-close-out` row when a new
  request turns out to be a regression of an earlier job. The template says what the counts do not mean (not a score of
  the agent). No statistics tool yet: it waits until there are rows to read.
- `devils-advocate` and `closeout-auditor` end their reports with an index table (`# | Severity | file:line | one line`);
  the body with evidence, scenario and proposal stays as it was. The index is what "Findings" counts.
- `closeout_check.py --plan <plan>`: new check `review-log` — the log exists, every row is well formed (columns, date,
  step, counts consistent; malformed rows are listed, never skipped) and there is a close-out row dated today. Without
  `--plan` the check prints SKIP. `/close-out` runs it once more before the report.
- `closeout_check.py` tried on a real project (1,221 Pascal / DFM files, 3–8 s): a finished job with three new forms and a
  data module gave the known answer, and three faults planted in a scratch clone (measure line, `CreateForm`, missing
  `{Form}` comment) were all found with their lines. The `.bak` check then reported `Project.exe.bak`, which an exe packer
  (ASPack) writes on every build; it now reports only backups of source files (`Unit1.pas.bak`, `Unit1.bak`,
  `notes.md.bak`), not build products.

**Skills**
- `/close-out` step 2 runs `closeout_check.py`; only the checks that need judgement stay manual.
- Round limits: `/build-check` stops after three fix-and-build rounds and hands over to the developer (no hiding messages
  to get under the limit); `/review` + `/multi-review` allow at most two review rounds per plan, then back to the
  hypothesis. Idea from bounded loops in multi-agent workflow engines.
- `/review` starts the `scope-counter` agent instead of an unnamed general-purpose agent; the four axes and extra
  questions, which were a near-verbatim copy of `scope-counter.md`, are removed from the skill. `/review` now also runs
  the `git status --short` check afterwards.

**Tests**
- `test_agents.py` (new): every `.claude/agents/*.md` has frontmatter with only known keys (Claude Code ignores unknown ones
  silently), `name` equal to the file name, a `tools` line (without it the agent inherits every tool) listing only Read,
  Grep, Glob, Bash, and is used by a skill.
- Total: 133 (was 56 at v0.4.0).

## v0.4.0 — 26.11.2026

Binary DFMs are now detected and reported at every level, line endings can be pinned with a `.gitattributes` example, and
installation has its own guide again.

**Binary DFMs (new)** — Claude and the tools can only read and edit text DFMs, and a `text` rule in `.gitattributes`
corrupts a binary one.
- `tools/dfm_text_check.py`: lists binary DFMs (resource header + `TPF0`, or a bare `TPF0` stream), skips IDE history
  folders, says how to convert (IDE "Text DFM", `convert.exe -i -t`); exit 1 if any. Never changes a file.
- `hooks/session_check.py` (SessionStart, matcher `startup`): if the project has binary DFMs, the list goes into Claude's
  context and Claude tells the developer in its first answer. Setting `warn_binary_dfm` (default true); the scan stops
  after 20 s on a very large tree. Wired in `examples/settings.json`.
- `pas_edit.py` refuses to edit a binary DFM; `pascal_check.py` reports one among changed files.

**Line endings**
- `examples/gitattributes` (copy to the project root as `.gitattributes`): Delphi sources stored with LF and always checked
  out with CRLF, independent of each machine's `core.autocrlf`; binary Delphi files never converted. The file says what it
  does not cover (a bare LF on disk until the next commit, the code page — `pascal_check.py` is still needed), the binary DFM
  warning, and the one-time `git add --renormalize .`. Suggested on Reddit.

**Documents**
- `docs/installation.md` and `docs/tr/kurulum.md` (new): requirements, installation (starting with the binary DFM check, with
  a `.gitattributes` step), every `claude-delphi.json` setting, tests, localization, databases, limits — the sections the
  shortened README no longer carried. The README links to it ("Getting Started"); its structure tree lists the new files.
- Mistake log [8] (English and Turkish): if a sibling covers the same area (two `alClient` controls), show in code which one
  is hidden on that path — the one later in the DFM is drawn on top. From a real case: a whole feature was built on a grid
  that a second, never-hidden `alClient` grid covered.

**Tests:** 56 (9 new: `test_dfm_text_check.py` 3, `test_session_check.py` 3, `test_pas_edit.py` 1, `test_pascal_check.py` 2).

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

**Tests:** 47 (was 32 at v0.1.0). `test_diff_routines.py` sets `core.autocrlf=false` in its temporary repository, so the
results do not depend on the machine's Git settings (with `autocrlf=true`, as on GitHub's Windows runners, a line-ending-only
change is no change at all).

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
