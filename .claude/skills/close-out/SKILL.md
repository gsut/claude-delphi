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

- Temporary measurement lines: `grep -rn "<measure marker>" --include=*.pas .` (marker from `.claude/claude-delphi.json`,
  default `X-MEASURE`) → 0 when the work is finished.
- Fix comments: every block starts with why it changed; the signature (initials + date) is on the last line only.
- A build was run after the last Pascal change (`/build-check`): 0 errors, 0 new warnings.
- No `.bak` file was created; no unwanted `CreateForm` in the `.dpr`.

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

- Test steps (which record type, which menu path; menu names from the DFM `Caption`, `Visible` checked).
- If there is a database script: file name and a note about the version number.
- If a data module changed: "close and reopen the project".

## 6. Report (these headings, short)

1. **How it was done** — file, routine, measurement, evidence.
2. **What the actual bug was** — root cause in one sentence; since when.
3. **Claude's own mistake** — where I was wrong in this job, who found it.
4. **Updated documents** — updated / not affected.
5. **Open items and tests** — what waits on the developer.

## 7. Mistake log

If the mistake under heading 3 of step 6 is of a **repeatable** kind, it is recorded in the same turn (see
`docs/mistake-log.md`):
- Only **one rule + one check** (a step whose execution can be seen) goes into the log. The log is loaded every session;
  the story goes into a separate source file, not into the log.
- If it repeats an existing item, no new item is opened: that item's check is strengthened.
- A one-off accident is not recorded. A mistake a pattern can catch goes into a hook, not the log; a job with known steps
  goes into a skill.
