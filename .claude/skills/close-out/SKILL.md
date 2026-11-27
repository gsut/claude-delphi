---
name: close-out
description: Close-out report and document update for a request / fix. Use when the work is done, or when the developer says "close", "close out", "report".
---

# Close-out

Before a job is called "done", the steps below are done in order; a skipped step is written as "not done" in the report.
Subject: $ARGUMENTS (if empty, the work done in this session).

## 1. Is the fix still active in the code

Show every fix line in today's source with `grep`. If it was commented out or removed, stop and ask.

## 2. Nothing left behind

- Mechanical checks: `python tools/closeout_check.py` (if the work is already committed: `--base <commit before the job>`).
  It checks that no measure-marker line is left, no `.bak` file exists, no `CreateForm` line was added to the `.dpr`, new
  forms are registered in the `.dpr` / `.dproj`, the last build is newer than the last change, and it notes a changed
  data module. Every FAIL is fixed, or written into the report with the reason it stays; NOTE lines go to step 5. Copy the
  tool's result lines into the report; do not redo these checks by hand.
- The build log being newer is not the result: the last `/build-check` must also have reported 0 errors, 0 new warnings.
- Fix comments: every block starts with why it changed; the signature (initials + date) is on the last line only.
- Every removed / narrowed / conditioned call is in the plan's "what the old call also did" table (mistake log [20]); if
  not, fill it now and add a test step for each row to step 5.

## 2b. Independent implementation audit (every close-out)

Goal: someone who did not do the work asks whether the plan was carried out, whether anything outside it was touched,
whether something broke. **Done before the commit**; if the work is already committed, the same steps run on the commit /
range. It costs a few minutes and tokens on purpose: in the project this comes from, it caught six real bugs in one
fifteen-file change before the commit, none of which the session's own checks had found.

**No file changes while the audit runs**: the map of step 1 and the agent must see the same tree. Documents are
updated in step 4, after the audit; a document listed in the plan's Scope therefore shows up in step 1's "not changed"
list, which is expected. If something must change during the audit (a finding is fixed), the audit runs again on the
new tree.

1. **Change map:** `python tools/diff_routines.py --plan <plan file>` (if committed: `--commit <rev>` or `--rev A..B`).
   It maps every hunk to a routine / DFM object and marks names that do not occur in the plan as "NOT IN PLAN" (for a
   plan written from `.claude/templates/plan.md`, only its Plan items and Scope sections count), and ends with the
   other direction: the Scope entries no change touched (a forgotten item, a contingency written in the wrong section,
   or a document still to update in step 4). Read the map yourself too: note which lines you can already explain.
2. **Agent:** `closeout-auditor` (`.claude/agents/`). The task text contains **only**:
   - the approved plan's file (written before coding, `/triage` step 7: `<personal folder>/plans/<id>-plan.md`);
   - how to get the diff (working tree, or commit / range) and the output of step 1;
   - the request document and its attachments, if any.

   No verdicts ("work is done", "it compiled, all fine"), no explanation of yours, no results of your own checks. If there
   is no plan file the agent still runs; the report says "no plan file, checked against the request text", and the plan
   from the conversation is **not** handed over in your own summary.
3. **Verification (mistake log [6]):** open every finding at its `file:line` yourself and accept or reject it; one line
   of reason for a rejection. A finding you cannot open goes to the developer as "reported by the audit, not verified".
   The agent fixes nothing; the fix of an accepted finding is asked of the developer. A clean audit does not replace
   sections 1, 2 and 3 of this skill. The agent is read-only by instruction and by `hooks/command_guard.py` (rule 6; a
   trip wire, not a boundary): note `git hash-object <plan file>` before starting it, and afterwards check that it is
   unchanged and that `git status --short` shows no unexpected change (it does not see the ignored personal folder).
4. **Review log:** after step 3, add a row to the review log next to the plan file (`<id>-plan.md` → `<id>-reviews.md`;
   copy `.claude/templates/reviews.md` if it does not exist yet): today's date, step `close-out`, agent
   `closeout-auditor`, Findings = rows of its index, Accepted / Accepted critical / Not opened from your verification.
   Over time the log shows whether the audit pays off, and whether small jobs need it; a regression found later is added
   as an `after-close-out` row (`/triage` step 5). Without a plan file there is no log; say so in the report.

## 3. Was each symptom explained by its own measurement

Write each symptom of the request on its own line: which measurement / experiment explains it? A symptom without a
measurement is marked "explained from code, not verified in data".

## 4. Documents

- **Pending work and test information is not written into documents in the repository;** it lives in the personal open
  issues list. A topic document in the repository receives only lasting information: structure, root cause, decision, result.
- Find other documents mentioning the subject with `grep -ln "<routine / topic name>" docs/*.md`; each is either updated
  or listed as "not affected" in the report.
- `.md` files are changed with Edit (not with scripts). Row contents read from the database and customer data are not
  written into documents in the repository.

## 5. Left for the developer

- Test steps (which record type, which menu path; menu names from the DFM `Caption`, `Visible` checked), starting from
  the test steps of the plan's [20] table; written into the plan file's Test steps section (`<!-- plan:tests -->`) too.
- If there is a database script: file name and a note about the version number.
- If a data module changed: "close and reopen the project".

## 6. Report (these headings, short)

If there is a plan file, run `python tools/closeout_check.py --plan <plan file>` once more before writing the report
(with `--base` as in step 2): the `review-log` line must be OK; copy the result lines into heading 3 (the audit in short).

1. **How it was done** — file, routine, measurement, evidence.
2. **What the actual bug was** — root cause in one sentence; since when.
3. **Claude's own mistake** — where I was wrong in this job, who found it (accepted findings of the step 2b audit
   included). Also the audit in short: plan items full / partial / missing, touches outside the plan, breakage candidates
   (accepted / rejected).
4. **Updated documents** — updated / not affected.
5. **Open items and tests** — what waits on the developer.

## 7. Mistake log

If the mistake under heading 3 of step 6 is of a **repeatable** kind, it is recorded in the same turn (see
`docs/mistake-log.md`):
- Only **one rule + one check** (a step whose execution can be seen) goes into the log. The log is loaded every session;
  the story goes into a separate source file, not into the log.
- If it repeats an existing item, no new item is opened: that item's check is strengthened.
- Deleting an item or loosening a check is only proposed (the developer decides at the monthly review); a check shown
  wrong by a measurement is fixed in the same turn and reported separately.
- A one-off accident is not recorded. A mistake a pattern can catch goes into a hook, not the log; a job with known steps
  goes into a skill.
