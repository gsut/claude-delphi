<!--
Plan file template. Copy to <personal folder>/plans/<id>-plan.md after the developer approves the plan (/triage step 7).
<id> = the ticket id, or the date and a short slug when there is none (2026-11-26-twin-rows).

The "plan:..." marker comments (each alone on its line) are fixed and must stay as they are; headings and text are
written in the developer's language. A section runs from its marker to the next marker. Tools read the markers, not the
headings:
  python tools/diff_routines.py --plan <file>   reads ONLY plan:items and plan:scope to decide "in plan" / "NOT IN PLAN".
So a routine name belongs in plan:items / plan:scope only if it will be changed; callers that stay as they are go into
plan:callers, steps that run only under a condition into plan:contingency. Evidence quotes and the [20] table may name
any routine without making it "in plan". The tool also reports the other direction: every `backticked` file, routine or
DFM object in plan:scope that no change touches.
Delete this comment in the copy.
-->

# <id> — <title>

<!-- plan:status -->
## Status

Approved by the developer: <date>. (Changed after review: <date> — what changed. Every change needs approval again.)

<!-- plan:request -->
## Request

Symptoms in the user's words, numbered; or the requested feature. Path of the request document, if any.

Deviations from the request (approved by <who>, <date>): what the plan does differently from the request text and why
(a name on screen that differs from the request, a part left out, a decision the developer made). "None" if there are
none — the close-out audit checks the implementation against the request too.

<!-- plan:hypothesis -->
## Hypothesis and evidence

Bug fix: the hypothesis (one sentence), the evidence (`file:line`, numbers from the data; story from code and measurement
marked separately), the measurement that confirmed it. Feature request: "none — feature request".

<!-- plan:items -->
## Plan items

Numbered; each item is one change the close-out audit can find in the diff. File, routine / DFM object, what changes.
When the same change goes to several places, list every place (the audit counts them one by one).

1. `Unit.pas` `TFormX.Routine`: ...

<!-- plan:scope -->
## Scope

Every file, routine and DFM object that will be changed, each in backticks, names exactly as in the source. Backticks
here only for those: a document section, a table row or a code fragment is written without them (the close-out map
lists every backticked entry that was not changed). Documents updated at close-out may be listed; the map then reminds.

- `Unit.pas`: `TFormX.Routine`, `TFormX.Other`
- `Unit.dfm`: `Grid1`

<!-- plan:callers -->
## Other callers (not changed)

Callers of the changed routines that stay as they are, and why the new behaviour is right for each.

<!-- plan:contingency -->
## Contingency items

Steps that are carried out only under a condition ("only if the click does not work in the trial; ask the developer
first"): the condition, the change, the files and routines it would touch. Not read by the tools, so these names are
neither "in plan" nor reported as not changed. If a contingency is carried out, move it into Plan items and Scope
(a plan change: update the status line, approval again).

<!-- plan:removed-calls -->
## Removed / narrowed / conditioned calls (mistake log [20])

| Call | What the old call also did | Test step |
|---|---|---|

Or "none".

<!-- plan:commit-point -->
## Commit point

For a change that writes data: on which event it runs, what remains if the user cancels. Otherwise "none".

<!-- plan:assumptions -->
## Assumptions

Added in /review or /multi-review step 1 ("the table has one row per record", "this form only opens from X"), together
with your own scope count on the four axes (calls, field accesses, DFM bindings, name strings) that the review is
compared with; empty until then.

<!-- plan:tests -->
## Test steps

Filled at close-out (/close-out step 5); may start with the test steps of the [20] table.
