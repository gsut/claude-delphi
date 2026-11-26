# Mistake log — method and starter items

A list of **repeatable** mistakes the AI makes in how it works. Pitfalls of the code base are not here; they live in a
separate "code pitfalls" document (`delphi-pitfalls.md`). This log is about the AI's own mistakes.

## Why a separate log

Adding a sentence to `CLAUDE.md` after every mistake soon stops working: the file grows, rules repeat each other, and
"be careful" sentences change nothing. The log avoids this with four rules:

1. **Every item is a rule + a check.** A check is a concrete step whose execution can be seen ("show it with `grep`",
   "run this query", "ask this"). "Be careful" is not a check.
2. **It stays short.** The log is loaded at the start of every session (`@docs/mistake-log.md` from `CLAUDE.md`). The
   story behind each item — date, job, what happened, who found it — lives in a separate source file that is not loaded.
3. **Merge before adding.** A new repeatable mistake is first compared with existing items: if it fits one, that item's
   check is strengthened; otherwise it is added as one rule + one check. A one-off accident is not added.
4. **A mistake a pattern can catch goes into a hook, not the log;** a job with known steps goes into a skill. The log is
   only for mistakes that need judgement.

Review it monthly with the developer; delete items that turned out to be useless. Item numbers never change (other
documents refer to them); merged items keep their old numbers in square brackets. The AI only **proposes** deleting an
item or loosening a check; the developer decides at the monthly review. A check shown wrong by a measurement is fixed in
the same turn and reported to the developer separately.

## Item template

```
**[n] <Rule: one sentence, imperative.>** <Optional one or two sentences of reasoning.>
*Check:* <step(s) whose execution can be seen>.
```

## Starter items

These are the parts of a log that grew over months in a legacy Delphi + database project which are not specific to that
project. When you take them into your own log, make them concrete with your project's names.

### Diagnosis and measurement

**[1] Measure first, then fix; show the experiment that tells the hypotheses apart.** A consistent story built from code
and "the numbers add up" are not evidence. Read the symptom word for word ("cannot be selected" ≠ "is not visible").
*Check:* if the diagnosis rests on code, propose a measurement line or a single-variable experiment before fixing; the
experiment must not change the measured variable as a side effect, and the measured path must be the path the user takes
(a command written into a document is tried exactly as written there — redirection and pipe included — and its output is
fed to the next step; on Windows, Python writes redirected output in the console code page, not UTF-8).
After a sentence like "it is slow because of X", if the question "how did I tell this apart?" has no counter or experiment
as its answer, add that measurement first.

**[2] Before interpreting a stored value, verify who wrote it and when.**
*Check:* before calling a value "corrupt" or putting it into a repair, list every writer of the column
(`grep -n "<Field>.Value :="`, stored procedures, triggers). Search the opening path of the screen that reads the value
for assignments that rewrite the field. Find out when the row was written: PostgreSQL — the row's `xmin` (rows written by
the same transaction share it; compare with rows of known date); SQL Server — a `rowversion` column, if the table has one;
MySQL / MariaDB and Firebird — no general equivalent: a "modified at" column, a trigger or the binary log / trace.

**[3] Old–new comparisons are made only with exes built from the same source and run the same way.**
*Check:* before taking a baseline, ask which exe it is and compare its build time with the last commit. Before changing
code because "the old one does not do it / the new one does", ask whether both exes were run the same way (from the IDE
or standalone; same parameters, database, steps).

**[4] Each symptom is measured separately in the data.**
*Check:* in the close-out report, each symptom on its own line: which measurement explains it? One without a measurement
is marked "explained from code, not verified in data".

**[5] Verify "none" and "this many" results.**
*Check:* before reporting absence, repeat the search case-insensitively and search, with the same method, for a name known
to exist (if the positive control is also 0, the method is broken). Before reporting a number, check for duplicate lines
(`sort | uniq -d` must print nothing); when counting code, filter out comment lines and open three results by hand.

**[6] A claim in a sub-agent's report is not presented to the developer as fact until you have verified it yourself.**
The report is another model's output: wrong things arrive with the same confidence.
*Check:* for every "the code does X" sentence carried from the report to the developer, open the file:line yourself (is the
call in a comment, what does the file on disk say); an unverified claim is marked "reported by the review, not verified by me".

**[7] Analysis does not start without searching our own documents.**
*Check:* `grep -rn -i "<name>" docs/*.md` with the relevant unit / routine / table names; read the documents found and mark
each finding "already documented / new".

### Screens, paths and tests

**[8] Find the form, the button and its name from the opening path and the DFM; do not guess from names in code.**
*Check:* from the user's action (`OnClick` / `OnExecute`) find which form is `Create`d; check for a second form with a
similar name. Search run-time `Caption :=` / `Visible :=` assignments. When writing test steps, read the object's parent
chain in the DFM (form → tab → panel), its `Caption` **and** its `Visible`.

**[9] Before asking for a test, build a reachability table; show that the branch really runs on the test record.**
*Check:* for every button / menu that calls the changed routine, read the `Visible` / `Enabled` assignments; state the
meaning of condition flags from where they are assigned, not from their names (`grep -n "<Flag> *:="`). "Same output" is
accepted only after showing that the changed line runs for that record. If nothing sets the triggering flag, write the
path down as "unreachable".

### Scope and generalisation

**[10] Before generalising a finding or stating a count, search the whole source; show every place with its line.**
*Check:*
- "The same pattern is also in X" → quote the line in X. "Dead code" → list every call line with its branch.
- Before stating how many copies a pattern has, search the whole source. Before calling something "dead", show which body
  the call line is in by matching `begin`/`end`: in Pascal, nested routines can start at column 0. `tools/pas_callers.py`
  does this and lists code references, other `{$IF}` branches, DFM bindings, name strings and comments separately.
- Before a bulk fix, show the path that reaches each copy (DFM event binding or call); the reachability list is the input
  of the edit script. Copies with no path are listed as dead and reported, not fixed.

**[20] Before removing, narrowing or conditioning a call, or choosing where a fix goes, read the caller side and everything
the old call did.**
*Check:*
- The plan has a table: each removed / narrowed / conditioned call → what the old call also did (when the condition is
  **not** met, before an early `exit`; side effects of `Close` or a cleanup) → test step. When a delete is narrowed to
  "only my rows", re-read the loops and queries that read the same table next.
- Before putting a fix next to one call, list all callers of the routine; if all share the defect, the fix goes inside the
  routine. Before changing a form's event handler, find every place that creates the form.

**[11] If an object's meaning will change, count the scope on four axes:** (1) calls — all spellings of the name;
(2) field accesses in the same routine after a call that changes position; (3) DFM bindings (`DataSource` /
`MasterSource` / `DataSet`); (4) places carrying the name as a string (`FindComponent`, templates, `FieldByName('…')`).
*Check:* confirm the count with a second method (`tools/pas_callers.py`, another pattern or `/review`). After every change to a DFM `DataSource`,
run `tools/dfm_field_check.py`.

**[12] In a "when did it break" range, look at your own changes first.**
*Check:* list all of your own changes in the range with files and dates (`git log --author`), then other people's; first
count the behaviour's counter in the logs day by day.

### The team's vocabulary and business rules

**[13] Do not guess the team's vocabulary or business rules.**
*Check:* if you are not sure what a field / state used in a decision means, ask; do not derive business rules by looking
at data. Before writing a decision question, list who reads the field and what the old code does today; ask only if the
old behaviour cannot be kept.

### Data and where the fix goes

**[14] Tie a lasting side effect to the commit point; enforce assumptions in code.**
*Check:* for a fix that changes data, find the form's save / apply point and compare the old value with the stored one
(tie it to a real difference, not to a click). An assumption written in a comment ("the table is unique", "the field is
filled") is also enforced in code (`LIMIT 1`, a constraint, a condition).

**[15] Fix the source of a derived column BEFORE the derivation runs.**
*Check:* verify, in code order, who reads the field being fixed and whether that read happens before or after the fix.

### Delphi and component behaviour

**[16] Innocent-looking reads, copies, locks and temporary changes in VCL / components have side effects.**
*Check:*
- Temporarily changed state (`Filtered`, `Enabled`, a global): save the previous value and restore it in `try … finally`
  (to the state it was found in, not to its default).
- `Edit` on an empty dataset calls `Insert` (`Data.DB` `TDataSet.Edit`); code that "only edits" can add a row.
- Before adding a lock (`BeginUpdate`, `DisableControls`), search the component source for the conditions it is used under.
- A cell lock given in a grid's `OnGetCellParams` (`Params.ReadOnly`) must also be given when `EditMode = True`: EhLib asks
  for edit permission exactly that way (`TAxisBarEh.CanModify`). `if EditMode then Exit` is only for colour and text. Add
  "double-click a locked cell and try to type" to the test steps.

**[17] Two traps the compiler catches.** Delphi `{ }` comments do not nest (a comment containing `{` uses `//`); an
anonymous method cannot capture a nested routine, a `var` / `out` parameter or `Result` (E2555). Details:
`delphi-pitfalls.md` §26.
*Check:* `/build-check`.

### Writing to files and documents

**[18] Rules for writing Pascal — the tools check most of them.**
- The hooks refuse / report: inline Python, `sed -i` on protected files, new bare LFs, a file saved with the wrong encoding.
- Pascal / DFM files are changed with `tools/pas_edit.py`: it keeps the code page and CRLF, refuses an anchor that does
  not occur exactly once, can limit the search to one routine (copies of a routine carry the same anchor) and, with
  `additions_only`, refuses a change that would remove or alter an existing line.
- *Manual check:* before rewriting a file the developer has fixed on disk, read the on-disk version. After the edit,
  `git diff --ignore-cr-at-eol -- <file>` shows only the intended lines; the written text is verified with `grep`.

**[19] Close-out: is the fix active in the code, are the documents current?**
*Check:* show the fix line in today's source with `grep`; find other documents mentioning the subject with `grep -ln` and
list each in the report as "updated / not affected" (`/close-out`).
