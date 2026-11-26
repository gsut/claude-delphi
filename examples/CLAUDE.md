# <Project name> — working notes for Claude (team)

Delphi (<version>; Win32 VCL) + <database> application. The project root is this folder (`<Project>.dpr`).
Components: <list>. Component sources: `<path>` (which ones have source, which are .dcu only).

This file holds the team's shared rules and is committed. Personal settings (initials for comment signatures, personal
folders) live in `CLAUDE.local.md`, which is not committed.

## Language

- Communicate with the developer in <language>. (Skills, agents and hook messages are in English; Claude follows them in
  any language. This line alone decides the language of answers and reports.)
- Code comments and commit-facing text: <language or English>.

## At the start of every session

1. Mistake log — Claude's repeatable mistakes (rule + check). Loaded automatically every session:
   @docs/mistake-log.md
2. For a new request: the code pitfalls document (`docs/delphi-pitfalls.md` + project-specific ones), the screen flow map,
   the table → code index ("who writes to this table").

## Way of working

- **Correctness over token savings.** When a step costs tokens or time but makes the result more reliable (a measurement,
  an independent review, a second count, the close-out audit), it is done. A step is skipped only when the developer says so.
- **Hypothesis first, then approval, then the fix.** "The cause is X, my evidence is Y" → developer approves → code. The
  approved plan is written to `<personal folder>\plans\<id>-plan.md` as approved, before any code (and updated if the plan
  changes); the close-out audit reads the plan from there.
- **Measure first.** A story built from code is weaker than a single-variable experiment; temporary measurement lines are
  added with the measure marker (`measure_marker` in `.claude/claude-delphi.json`, default `X-MEASURE`) and removed when
  the work is done.
- **The best solution, not the fastest**; a quick patch only when explicitly asked.
- **Surgical changes.** Only the lines the request needs; adjacent code, formatting and dead code are not touched (dead code
  is reported; once a review confirms it is dead it gets the dead-code marker, it is not deleted).
- **Merging copies is preferred.** If a change touches routines that are copies of each other, the plan merges them into a
  shared routine.
- **At the end of every fix:** how it was done, what the actual bug was, what Claude's own mistake was. A repeatable mistake
  goes into the mistake log in the same turn (rule + check).
- **Build verification is Claude's job** (`/build-check`): 0 errors and 0 new warnings vs baseline. Testing and deployment
  are the developer's.
- **Git is read-only** (log, show, diff, blame, archive). Claude does not commit, push, check out etc. The GitHub CLI is
  read-only too (`view`, `list`, `gh api` GET); creating, editing, commenting and releasing are the developer's.

## Code rules

- **Dead-code marker** (`dead_code_marker` in `.claude/claude-delphi.json`, default `DEAD-CODE`; the examples below use the
  default): a block confirmed dead by review is not deleted; above it goes `// DEAD-CODE: <evidence>. <initials> - <date>`. Evidence is short and repeatable: results of searching for callers / DFM
  bindings / name strings (`python tools/pas_callers.py <Name>` prints all of them and a ready evidence line). Deleting is a separate cleanup decision; candidate list `grep -rn "DEAD-CODE:" --include=*.pas .`.
- Pascal sources are **<code page> + CRLF**. DFMs are ASCII; non-ASCII characters as `#nnn` escapes. `.md` files are UTF-8.
- Pascal / DFM files are changed with `tools/pas_edit.py` (keeps the code page and CRLF; the anchor must occur exactly
  once; `routine` limits the search to one routine; `additions_only` for pure insertions); no `sed -i` or shell
  redirection (the hook refuses them).
- Every fix block starts with a comment explaining what changed and why; the **last line of the explanation ends with**
  `<initials> - <date>`.
- Delphi `{ }` comments do not nest; a comment containing `{` uses `//`.
- **If a data module unit is touched, the report says so** (the IDE may not compile an externally changed data module
  correctly; close and reopen the project).
- Every form with visuals is written with a DFM (editable in the IDE); no forms built in code.

## Database

- Claude's access is read-only (`<read-only user>`). Data or schema changes are delivered as scripts.
- In multi-tenant / per-file tables, **every UPDATE / DELETE** is checked for the tenant condition.
- Row contents read from the database are not written into committed documents or persistent memory (schema information
  may be).

## Tool checks and commands (`.claude\`, committed)

- `hooks\session_check.py` — at session start, lists binary DFMs if the project has any. If it does, tell the developer in
  the first answer and do not touch those files: they must be converted to text first (IDE: right-click the form > Text DFM).
- `hooks\command_guard.py` — refuses inline Python, `sed -i` / redirection on protected files, write-access DB users,
  GitHub CLI commands that write.
- `hooks\pascal_check.py` — reports new bare LFs, wrong encoding, project-specific forbidden patterns, double signatures
  and binary DFMs in changed Pascal / DFM files (compared with the committed version).
- Tools (`tools\`): `pas_edit.py` (the only way Pascal / DFM files are edited), `pas_callers.py` (references and dead-code
  evidence), `dfm_field_check.py` / `dfm_field_usage.py` (DFM bindings), `pg_fingerprint.py` (before / after data diff),
  `diff_routines.py` (change map: diff hunks → routines / DFM objects, checked against the plan), `dfm_text_check.py`
  (binary DFM list).
- Commands: `/build-check`, `/triage`, `/review`, `/multi-review`, `/close-out` (with the independent `closeout-auditor`
  agent before the commit).
- A new mistake that a pattern can catch goes into these checks, not into the mistake log.

## Not committed

- `CLAUDE.local.md`, the personal folder (pending work, test lists, SQL scripts, log copies, anything with customer data),
  build output.
