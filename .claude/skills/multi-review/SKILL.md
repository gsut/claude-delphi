---
name: multi-review
description: Extended /review — has a change plan read in parallel by two context-free agents (scope-counter counts the scope, devils-advocate looks for failure scenarios). Use after the plan is approved and before code is written. Usage /multi-review <subject of the plan>.
---

# Multi-agent review

Subject: $ARGUMENTS

The main session implements; there is no separate implementing agent.

When: structural changes, merging copies, changes that write data or have many callers, and feature requests. Not for a
small single-routine bug fix. For bug fixes, review the fix plan after the measurement, not the hypothesis.

## 1. Write your own count first

Before starting the agents, write your own scope count on four axes: calls, field accesses, DFM bindings, name strings.
For calls, DFM bindings and name strings `python tools/pas_callers.py <Name>` gives a first list.
Also list the plan's assumptions one by one ("the table has one row per record", "this form only opens from X") and
write them, together with your scope count, into the plan file's Assumptions section (`<!-- plan:assumptions -->`, see
`/triage` step 7).

## 2. Start both agents in parallel, in one message

- `scope-counter`: the task text contains only the object(s) that will change (routine / dataset / form and file) and the
  description of the change (what is moved, removed, merged). **No assumption list and no conclusion of the plan.**
- `devils-advocate`: the same description + the assumption list from step 1 + the plan's "removed / narrowed call → what
  the old call also did" table (mistake log [20]; the plan file's `plan:removed-calls` section; if there is no plan file
  or table, write "no table") + the path of the request document, if any. No judgement sentences ("we think it is safe").

Both agents are read-only by instruction and by `hooks/command_guard.py` (rule 6 refuses the usual ways a Bash command
writes; a trip wire, not a boundary). Before starting them, note `git hash-object <plan file>`; afterwards check that it
is unchanged and that `git status --short` shows no unexpected change (it does not see ignored folders such as the
personal folder, hence the hash).

## 3. Compare and verify

| Axis | My count | Scope counter | Difference (file:line) | Decision |
|---|---|---|---|---|

| Finding | Severity | Did I open the evidence myself (file:line) | Decision: accept / reject (why) / ask the developer |
|---|---|---|---|

- Open every difference and every finding in the source yourself. An agent's finding can be wrong; an unopened finding is
  not presented to the developer as fact but marked "reported by the review, not verified by me".
- Verify every "none found" search by finding a name known to exist with the same method.
- An objection without evidence does not overturn a measured finding; at most it becomes a proposal for a new measurement.

## 4. Result

Short report to the developer: accepted findings (risk + step added to the plan), cases added to the test list, rejected
ones (one-line reason), open "not verified" items. If the plan changes, read its [20] table (`plan:removed-calls`)
again — a plan that grew under review often removes or narrows a call it did not before — and get approval again
before writing code.

**At most two review rounds per plan** (`/review` and `/multi-review` together). If the changed plan is reviewed again and
that second review changes it once more, do not start a third: take the open findings to the developer and go back to
the hypothesis. A plan that keeps moving under review usually rests on a wrong assumption, not on a missing step.

## 5. Review log

After step 3, add one row per agent to the review log next to the plan file (`<id>-plan.md` → `<id>-reviews.md`; copy
`.claude/templates/reviews.md` if it does not exist yet; the column meanings are in the template): step `multi-review`,
the round number, `scope-counter` (Findings = differences between your count and its count, plus findings in its
answers to the extra questions) and `devils-advocate`
(Findings = rows of its index). The counts come from your step 3 tables, after you opened the evidence, not from the
agents' reports. Write the file with Write / Edit.
