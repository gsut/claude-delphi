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
Also list the plan's assumptions one by one ("the table has one row per record", "this form only opens from X").

## 2. Start both agents in parallel, in one message

- `scope-counter`: the task text contains only the object(s) that will change (routine / dataset / form and file) and the
  description of the change (what is moved, removed, merged). **No assumption list and no conclusion of the plan.**
- `devils-advocate`: the same description + the assumption list from step 1 + the path of the request document, if any.
  No judgement sentences ("we think it is safe").

Both agents are instructed to be read-only; only the instruction keeps them from using Bash to write. Afterwards, check with
`git status --short` that the working tree has no unexpected changes.

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
ones (one-line reason), open "not verified" items. If the plan changes, get approval again before writing code.

## 5. Measurement (optional)

To see whether the review pays off, add a row to a table: date, subject, scope differences (accepted / total), advocate
findings (accepted / total, number critical). If a problem not in the plan appears after implementation, note it on the same row.
