# Case study: the empty twin rows

A real case from a legacy Delphi VCL + PostgreSQL application, told with names removed. It shows the method of this
repository at work — including the places where the AI was wrong and what caught it.

## The setting

The application keeps one **summary row per document and period** in a table. Many screens read it; reports total it
across periods; several SQL statements read "the" row with `LIMIT 1` or join it in an `UPDATE … FROM`.

On screen the summary is a `TDataSet` in a master-detail link: the master is a "management" dataset whose current row
says which document is open; the detail shows that document's rows, filtered on the client to the current period
(`OnFilterRecord`). Its `OnNewRecord` fills a handful of defaults (a tax rate, a "included" flag, the document key and
the period number from global variables).

## Symptom

While working on something else, a read-only query showed that the table was **not unique** on (document, period):
17 duplicate groups, and in 9 of them the rows had different values. Every `LIMIT 1` read and every `UPDATE … FROM` on
those documents picked one of the rows at random.

## Step 1 — do not clean before you know the source

The obvious move was a unique constraint plus a cleanup script. The developer stopped it: *"First find out what produces
the empty rows. Let's fix it before it happens."* A cleanup without a known source just schedules the next cleanup.

## Step 2 — let the data say who wrote the rows

Comparing the extra rows column by column, **every one of them carried exactly the `OnNewRecord` defaults and nothing
else**. That ruled out the SQL paths (none of them write those defaults) and pointed at the client: something called
`Append` / `Insert` on the summary dataset while it looked empty.

Rows that belonged to "library" documents (special documents used as reusable books, not real projects) were among them,
which gave the next clue.

## Step 3 — a hypothesis from code, then an experiment

Reading the code produced a story: a menu command that opens a library book moves the **master cursor** to the book;
when it finishes, a "restore state" routine puts the global variables back, but not the cursor. The detail dataset now
follows the wrong master row, a later "is the summary approved?" check finds it empty and appends a row.

A story from code is not evidence, so the next step was a single-variable experiment the developer ran:

1. note the highest row id in the table;
2. open document A;
3. open library book B from the menu, close it;
4. look at rows with a higher id.

Result: one new row, for book B, with the period number of document A and two values copied from document A. The
hypothesis held.

## Step 4 — the plan, and the review that changed it

The first plan: route the seven `Append` calls on the summary dataset through one guarded routine that refuses to insert
when the master is on the wrong document.

Because this changes the behaviour of a dataset used by many screens, it went through `/review`: an independent agent got
only the description of the change (not the hypothesis, not the conclusion) and counted the scope on four axes. It came
back with something the plan had missed:

> `TDataSet.Edit` on an **empty** dataset calls `Insert` (`Data.DB`).

The code had about 62 unconditional `Edit` calls on that dataset, plus data-aware controls bound to it. Guarding the seven
`Append`s would have left dozens of ways to create the same row. The AI opened `Data.DB.pas` and confirmed it before
taking it to the developer (an agent's claim is not presented as fact until verified), and the plan was re-approved in a
new form:

1. **Fix the source:** the restore routine also moves the master cursor back to the open document, and the two menu
   commands wrap their body in `try … finally` so the restore runs on early exits and errors too.
2. **Measure what is left:** a `BeforeInsert` handler on the summary dataset logs a warning (it does not block) when an
   insert happens in a suspicious state: no open document, a library book, the cursor on another document, or a row for
   that document and period already in the database. `BeforeInsert` sees every path — `Append`, `Insert`, `Edit` on an
   empty set and data-aware controls.
3. **Clean the existing data in the repair tool,** not at program start: rows with no document, rows of inactive library
   books, and empty twins that have a filled sibling. Run against the local database first as a read-only count.

## Step 5 — what the follow-up found

Closing the item meant looking at the "reported, out of scope" notes as well:

- **Reading the previous period** was done in five copies by temporarily setting the global period number to N-1,
  re-filtering, reading a field and setting it back — without `try … finally`. An exception in between would leave every
  later write going to the previous period. The copies were merged into one routine that restores in `finally`
  ([pitfall 4](delphi-pitfalls.md#4-a-flag-or-global-is-changed-without-tryfinally), [16](delphi-pitfalls.md#16-a-fix-in-copied-code-reaches-only-one-copy)).
  Two of the copies used a different "real period" variable because another screen renumbers the global one; the
  review found that too.
- To show the merge changed nothing, a **fingerprint** of every row of two test documents was taken before and after
  running the affected screens (`tools/pg_fingerprint.py`): only the current period's summary row changed, the previous
  period's row did not — the period number was restored correctly.
- A remaining orphan row was traced through the logs and the rows' `xmin` to an old version of "delete last period" that
  did not update the document's current period; a guard added a few days earlier already prevents it, and a repair step now
  removes rows numbered beyond the last period.

## The AI's own mistakes during this work

- In a related item of the same series, it predicted from code that a missing period would fall back to January. A
  measurement showed the price actually came from whatever row a lookup cursor was left on. The prediction was withdrawn
  and the item rewritten.
- It counted 8 callers of a routine; the caller tool later found 9 — an earlier `grep` output had been cut with `head`.
- While building the edit tool for this repository, it first explained a failing test as a diff-tool artefact; the real
  cause was an anchor matching inside a more indented line. The tool now matches whole-line anchors only at line starts.

Each of these went into the mistake log as a rule + a check, or into a tool, in the same turn.

## What made the difference

| Step | Practice |
|---|---|
| Not adding a constraint first | find the source before cleaning ([mistake log](mistake-log.md) [1]) |
| Defaults in the extra rows | let the data say who wrote it ([2]) |
| Menu experiment with ids | a single-variable experiment instead of a story ([1]) |
| `Edit` = `Insert` | a blind review counting scope on four axes ([11]); verifying the agent's claim ([6]) |
| `BeforeInsert` warning | measure the remaining paths instead of guessing them |
| Cleanup in the repair tool | lasting side effects tied to an explicit action, not to program start ([14]) |
| Fingerprint before / after | show that a refactor changed nothing ([4]) |
