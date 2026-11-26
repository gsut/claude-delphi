# Delphi + database: recurring pitfalls

Patterns that repeatedly made diagnosis longer when working with AI on a legacy Delphi VCL + database code base
(UniDAC / FireDAC / ADO-style `TDataSet` components). All of them come from real cases; each item has the symptom, the root
cause, how to catch it and a fix pattern. Checking here first on a new request rules out four or five hypotheses without
trying them.

Treat this document as a starting point in your own project and grow it with your own cases.

---

## 1. Plain SQL was written, the open dataset did not see it

**Symptom.** The data is correct in the database but missing on screen or in a report.

**Root cause.** A table component keeps a client-side buffer. An `insert` / `update` executed through a separate query is not
reported to a dataset that is **already open** on that table; the dataset only learns about it when closed and reopened or
`Refresh`ed.

**Catch it.** Check the server's statement statistics for a `SELECT` on that table; if there is none, the dataset was
never opened. PostgreSQL: `pg_stat_statements`; SQL Server: Query Store or `sys.dm_exec_query_stats` +
`sys.dm_exec_sql_text`; MySQL / MariaDB: `performance_schema.events_statements_summary_by_digest`; Firebird: `MON$STATEMENTS`
(only statements active at the moment) or the trace API.

**Fix pattern.** Right after the writing code: `Close; Open; First;`. `First` matters: report bands often look at the
**current row**, and with the cursor at EOF the condition fails.

## 2. A client-side filter was left off → records mixed up

**Symptom.** An "already done" warning on a clean record; the program behaves as if another record's data were present.

**Root cause.** There is no server-side filter: the whole table is fetched and filtered on the client in
`OnFilterRecord`. The moment `Filtered := False`, rows of **all tenants** are visible in the buffer.

**Fix pattern.** Move filtering to the server (the component's `FilterSQL` / `Params` / a master-detail link); the client
filter can stay. Every place that changes a filter temporarily restores it with `try … finally` to the state it found.

## 3. SQL was written, the flow overwrote it later

**Symptom.** While debugging, the value **becomes correct and then breaks again**.

**Root cause.** Another statement touches the same table later in the flow ("reset everything first, then fill"; the fill
covers only one side).

**Catch it.** Dump **every** statement that wrote to the table, as executed:
PostgreSQL:
`select calls, rows, query from pg_stat_statements where query ~* '(update|insert into|delete from)\s+<table>'`.
SQL Server: Query Store / `sys.dm_exec_query_stats` filtered on the statement text; MySQL / MariaDB:
`performance_schema.events_statements_summary_by_digest` (`DIGEST_TEXT`); Firebird: a trace session on the table.
If the row's `id` changed, the row was deleted and rebuilt; if not, it was overwritten.

**Lesson.** Before writing to a table, ask: *who touches this table after me in this flow?*

## 4. A flag or global is changed without `try…finally`

**Symptom.** After an operation part of the screen "freezes"; or later writes go to the wrong record.

**Root cause.** Between `Flag := True; … Flag := False;` (or `Old := Global; Global := X; … Global := Old;`) there is an
`exit` or an exception; the value stays stuck. If the global is the key of a filter (for example "current period
number") and is not restored, every following record write goes to the wrong row.

**Second defect: nesting.** With a plain `Boolean`, an inner block resetting the flag breaks the outer block's protection.

**Fix pattern.** A counter + `try…finally` (`BeginUpdate/EndUpdate` semantics); move the temporary global change into a
single shared routine that restores it in `finally`. If the pattern exists in several copies, merge them (item 16).

## 5. One-way update (latch)

**Symptom.** Once an indicator shows "on", it is never cleared again.

**Root cause.** The event handler only writes the "present" state; there is no `else` writing "absent"; or an `else if`
chain updates only the first condition.

**Fix pattern.** Each indicator is written **independently and both ways** from its own data.

## 6. The helper swallows the error — but logs it

"Execute SQL" helper routines often log the error in `except` and carry on. If a statement seems to have done nothing,
**check the log first**. New code that swallows an error at least writes it to the log.

## 7. `KeyFields = 'id'` + `StrictUpdate = False`

Every `Post` and `RefreshRecord` goes to the server as `UPDATE … WHERE id = N`. Without an index on `id`, every write is a
full table scan. `StrictUpdate = False` swallows the "N rows affected instead of 1" warning and can hide duplicate `id`s
for months.

## 8. Repetition on the client = a fixed cost

A `TField.Value := …` assignment triggers `DataEvent(deFieldChange)` and every bound control refreshes itself; hundreds of
milliseconds per assignment can be measured on a busy screen. A server round trip is also a fixed cost; a row-by-row loop
multiplies it. **Fix:** turn the loop into set-based SQL, or find the expensive receiver and silence only that (item 13).

## 9. A second copy of stored procedure logic in Delphi

When the last steps of a procedure are copied into Delphi for a quick fix, the copy silently falls behind when the
procedure changes. Before opening a new copy: is it really impossible to solve it in the procedure itself?

## 10. Improving the path you measured, not the path the user takes

**Symptom.** After a performance fix the measurement looks great, but the user says "better, but still slow" — the
signature of a partial fix.

**Rule.**
- Start measuring **from the key the user presses**, not from the routine you found.
- List **every** entry point that triggers the operation: button, grid event, keyboard shortcut, dataset event
  (`OnNewRecord`, `OnCalcFields`, `AfterEdit`).
- After the fix, run **the tester's scenario exactly**.

## 11. Writing the same value to a UI property is not free

Writing a control property (`ImageIndex`, `Caption`, `Color`, `Enabled`, `Visible`, `Hint`) unconditionally from a
frequently running routine (`OnDataChange`, `OnCalcFields`, `OnGetCellParams`) means a repaint every time. Compare first:
`if X.ImageIndex <> New then X.ImageIndex := New;`. Add visible flicker to the symptom list: every flicker is an
unnecessary repaint.

## 12. On a path that never ran, templates and data are suspect too

If a feature **never ran** in the field, nothing on its path is verified: not the code, not the report template, not the
default settings or table contents. "Did this path ever work?" is the first question of the diagnosis; if not, compare
with a working member of the same family before reading code.

## 13. Do not call `DisableControls` from inside an event handler

If `DisableControls / EnableControls` is called while a bound control's event (`OnColExit`, `OnKeyDown`, `OnExit`) is
running, `EnableControls` sends the grid a bulk "dataset changed"; the grid refreshes in the middle of its own operation and
the pending keyboard action is lost. If notifications must be suppressed for speed, silence the actual expensive receiver.
After a performance fix, also test the screen's **keyboard flow**.

## 14. Delphi's "first row" becomes "all rows" in SQL

A lookup done with `Locate`, `FieldByName` (first record) or `RecordCount > 0` has "at most one row" semantics. When moving
the logic into SQL, write that **into the code**: `LATERAL (... ORDER BY ... LIMIT 1)` or a constraint guaranteeing
uniqueness. Unexpected duplication in an aggregating query is always first tested as JOIN fan-out.

## 15. `Edit` on an empty dataset = `Insert`

`TDataSet.Edit` calls `Insert` on an empty dataset. Code believed to "only edit" — or a user typing into a DB control bound
to the dataset — adds a new row if the dataset happens to be empty because of a filter or a master-detail link. This is
often the source of unexpected "empty twin" rows. To catch it: a temporary measurement warning in the dataset's
`BeforeInsert` (who is inserting, in which state). The full story: [case study](case-study.md).

## 16. A fix in copied code reaches only one copy

When fixing a bug, look for other copies of the same logic: routine name, table name, a key line. If there are copies, do
not carry the fix to each copy; merge them into one routine and make the others call it. `tools/pas_callers.py` lists every
use of the routine you introduce (to show all copies now call it); `tools/pas_edit.py` with `routine` edits one copy without
touching the identical lines of the others.

## 17. `SetFocus` on a control on a hidden tab

If the control is on a tab that is not in front, or on a form not shown yet, `SetFocus` raises "Cannot focus a disabled or
invisible window". `if X.CanFocus then X.SetFocus;` — `CanFocus` checks that the control and **all its parents** are
visible and enabled.

## 18. A forgotten tenant condition

In multi-tenant / per-file tables, a statement touching **only the open record** is not guaranteed unless the condition is
written. Copied records carry the same internal ids, so fields that are "unique within a record" are not unique across
records. **Catch it:** in every UPDATE / DELETE, is there a tenant condition in the `where`; in an `UPDATE … FROM`, is the
target table's tenant in the condition, or only the source side's?

## 19. Unparenthesised `or` + a tenant condition appended as a string

If the tenant condition is appended to the end of the statement as a string (`' and TenantId = ...'`), `where a or b` plus
the suffix becomes `a or (b and TenantId = X)`: rows satisfying `a` are updated or deleted **in all tenants**. Reading the
code, the condition "is there"; the bug is only in precedence. In every statement with `or`, is the condition in parentheses?

## 20. A screen control is not set from the data, only changed by clicks

If a control's `OnChange` writes a field but the control itself is not set from that field when the screen opens, the
screen shows one thing while the program works by another. Wherever the field is read, the control's value is set too (with
its event temporarily disabled).

## 21. `FieldByName('X').Value = ''`: always False on NULL

`Value` returns a Variant; if the field is NULL, `Value = ''` is False and `Value <> ''` is True. If both empty text and
NULL mean "no value", the code treats NULL as "filled". Typed field access and `AsString` return `''` for NULL; if the same
column is read both ways in two places, the two places decide differently.

## 22. Names mislead; read the whole grep result

Read a settings column by what the code that fills it does, not by its name. Before saying "this flag is never True", read
every assignment line; one missed line turns a "dead" verdict wrong.

## 23. A dataset without a master link + `Refresh` in a loop = the whole table, again and again

A `TUniTable` / `TFDTable` that filters its records on the client (`OnFilterRecord`, a `Locate` by tenant) still fetches
**every tenant's rows** from the server. `Refresh` inside a row loop fetches the whole table once per row: in a real case
15 rows took 10.5 s (108 k rows, 104 MB) and 0.2 s after the dataset was linked to the tenant master
(`MasterSource` / `MasterFields`). Do not simply delete the `Refresh`: check first whether it makes the dataset see a value
that SQL wrote in between (a "delete later" mark that the loop clears row by row) — without it the stale value can delete
valid rows.

## 24. Selecting tree nodes one by one to reach a target fires the change event every time

A routine that walks a `TTreeView` by setting `Selected := Selected.GetNext` until it finds a node runs `OnChange` for
every node on the way — often a query and a recalculation each. Find the node from its data (`Node.Data`) and select only
that one; keep the old loop as a fallback if the check after the selection does not hold.

## 25. Over a network, count server round trips, not server time

A screen that takes 2.5 s locally may take 10 s over a network, and the server's own time says nothing about it
(186 ms in a real case). The number that matters is the number of statements per user action:
`pg_stat_statements_reset()` → do the action once → `select calls, query from pg_stat_statements order by calls desc`.
Look for statements with hundreds of calls — and for queries whose result is never used: in the real case 100 of 339 were
a per-group `SUM` whose result was opened and closed without being read. Each new SQL text also costs the data-access
layer a metadata query (UniDAC field info), so the waste doubles.

## 26. Short compiler and component traps

- **`{ }` comments do not nest:** a comment containing `{` is written with `//` or `(* *)`; otherwise the first `}` closes
  the comment and the rest is compiled as code.
- **Anonymous methods (E2555 "Cannot capture symbol")** cannot capture a nested routine, a `var` / `out` parameter or
  `Result`; move the nested routine's code into the anonymous method or make it a class method. The build check catches both.
- **UniDAC: turning off `DefaultValues`** makes a NOT NULL column with a server default Required on the client; `Post` fails
  before reaching the server ("Field '…' must have a value"). Set `Options.RequiredFields := False` too; find the columns in
  `information_schema.columns` (`is_nullable = 'NO'` and `column_default` set).
