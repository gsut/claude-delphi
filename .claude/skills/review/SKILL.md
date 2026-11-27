---
name: review
description: Independent (context-free) second reading of a structural change plan. Use when the meaning of a dataset, a routine or a flow order will change, after the plan is approved and before code is written. Usage /review <subject of the plan>.
---

# Independent review

Subject: $ARGUMENTS

Goal: find what the session that wrote the plan did not see. So the review is done by **a separate agent**, and it is given
only what will change, not the plan's conclusion (an agent handed a hypothesis tends to return it confirmed).

## 1. Write your own count first

Before starting the review, write your own scope count on four axes (for comparison): calls, field accesses, DFM bindings,
name strings. For calls, DFM bindings and name strings `python tools/pas_callers.py <Name>` gives a first list. Put it
into the plan file's Assumptions section (`<!-- plan:assumptions -->`).

## 2. Start the agent

Start the `scope-counter` agent (`.claude/agents/`). Its definition holds the rules, the four axes (calls, field accesses
and order dependence, DFM bindings, name strings), the extra questions and the report format; do not repeat them in the
task. The task text contains the following and **nothing else**:

- The object(s) that will change: routine / dataset / form name and file.
- A description of the change (what is moved, removed, merged) — without judgement sentences such as "we think it is safe".
- Where to read, if it is not the project root: component sources, the code pitfalls document.

No assumption list and no conclusion of the plan. The agent is read-only by instruction and by `hooks/command_guard.py`
(rule 6; a trip wire, not a boundary). Before starting it, note `git hash-object <plan file>`; afterwards check that it
is unchanged and that `git status --short` shows no unexpected change (it does not see ignored folders such as the
personal folder, hence the hash).

## 3. Compare

Put the agent's findings next to your own count:

| Axis | My count | Review's count | Difference (file:line) |
|---|---|---|---|

- Open every difference in the source yourself; the agent can be wrong too, and a finding without a quote does not count.
- Verify every "none found" search by finding a name known to exist with the same method.

## 4. Result

Short report to the developer: confirmed pitfalls (risk + proposed safeguard), steps added to / changed in the plan, cases
added to the test list, open "not verified" items. If the plan changes, read its [20] table (`plan:removed-calls`)
again — a plan that grew under review often removes or narrows a call it did not before — and get approval again
before writing code.

Add one row to the review log next to the plan file (`<id>-plan.md` → `<id>-reviews.md`; copy
`.claude/templates/reviews.md` if it does not exist yet): step `review`, the round number, agent `scope-counter`,
Findings = differences between your count and its count, plus findings in its answers to the extra questions, after
you opened them in step 3.

**At most two review rounds per plan** (`/review` and `/multi-review` together). If the changed plan is reviewed again and
that second review changes it once more, do not start a third: take the open findings to the developer and go back to
the hypothesis. A plan that keeps moving under review usually rests on a wrong assumption, not on a missing step.
