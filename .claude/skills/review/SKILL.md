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
name strings. For calls, DFM bindings and name strings `python tools/pas_callers.py <Name>` gives a first list.

## 2. Start the agent

One general-purpose agent, read-only. The task text contains the following and **nothing else**:

- The object(s) that will change: routine / dataset / form name and file.
- A description of the change (what is moved, removed, merged) — without judgement sentences such as "we think it is safe".
- Where to read: project root, component sources, the code pitfalls document.
- Rules: change no file; quote every finding as `file:line`; mark anything uncertain as "not verified".

The four axes requested:

1. **Calls:** every call / use of the object (all spellings of the name, case-insensitive, including ones ending a line);
   copy units not in the `.dpr` listed separately.
2. **Field accesses and order dependence:** field reads / writes in the same routine after a call that changes position
   (`Locate`, `Open`, `Close`, filter); reads between the old and new place of a moved step; master-detail datasets
   (DFM `MasterSource`).
3. **DFM bindings:** `DataSource` / `DataSet` / `MasterSource` = … lines and run-time assignments (`DataSource :=`); does
   the field exist in the new dataset, with the same class?
4. **Name strings:** places that carry the name as text — `FindComponent`, `FieldByName('…')`, report templates, database
   functions and views.

Extra questions:

- Did the removed / conditioned call also do work when the condition is **not** met (lines before an early exit)?
- **Every** caller that opens the changed routine or form (`T<Form>.Create`); should the behaviour change for all of them?
- Does temporarily changed state (filter, `Enabled`, a global) return to the state it was found in?
- Do statements writing to multi-tenant / per-file tables include the tenant condition?

## 3. Compare

Put the agent's findings next to your own count:

| Axis | My count | Review's count | Difference (file:line) |
|---|---|---|---|

- Open every difference in the source yourself; the agent can be wrong too, and a finding without a quote does not count.
- Verify every "none found" search by finding a name known to exist with the same method.

## 4. Result

Short report to the developer: confirmed pitfalls (risk + proposed safeguard), steps added to / changed in the plan, cases
added to the test list, open "not verified" items. If the plan changes, get approval again before writing code.
