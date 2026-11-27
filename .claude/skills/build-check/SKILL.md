---
name: build-check
description: Delphi build verification. Use after every Pascal / DFM change and when the developer says "build"; reports errors and the number of warnings that are new compared with the baseline.
---

# Build check

Output, dcu files and logs go only under `build\`; the developer's exe / dcu files are never touched.

## Steps

1. Before building, list the changed files: `git status --short -- "*.pas" "*.dfm" "*.dpr" "*.dproj"`.
2. Run it (can take a few minutes; use a long timeout): `cmd //c "build\\build.bat"`.
3. Read the summary (last lines of the script; full log in `build\log\last.log`).
4. Acceptance: **0 errors and 0 "new warnings/hints vs baseline".**
   - On errors: open the file and line of the first error, fix it, build again. Later errors are often caused by the first.
   - On new warnings: either remove them or state in the report why they stay; never add them to the baseline on your own.
   - **At most three fix-and-build rounds per job.** If the third build still has errors or new warnings, stop: report
     the remaining messages, what each round changed and why it did not help, and ask the developer. Do not start a
     fourth round, and do not get under the limit by hiding a message (`{$WARN … OFF}`, `{$HINTS OFF}`, a new baseline,
     commenting code out). Three failed rounds usually mean the change or its premise is wrong, not the last edit.
5. Report (short): what was built, number of errors, number of new warnings, how many rounds it took, and whichever
   notes below apply.

## Notes to add to the report

`python tools/closeout_check.py` reports the first two mechanically (lines `data-module`, `createform`, `new-form`).

- If a data module (`TDataModule`) unit changed: **"data module changed — close and reopen the project in Delphi"**
  (the IDE may compile an externally changed data module from its in-memory copy).
- If a new form / unit was added: no unwanted `Application.CreateForm` line in the `.dpr`; the form name appears in the
  `.dpr` comment and in the `.dproj` `<Form>` tag.
- A successful build does not mean the program was tried: the report says "built" and "tested" separately.

## Do not

- Refresh the baseline (`build.bat baseline`) except in two cases: the developer asks for it, or it is the first build
  after the developer's commit (`git log -1` changed **and** none of your own changes are in the working tree). Never take
  a baseline while your own change is on disk (it would bury the new warnings in the baseline); when in doubt, ask.
- Run the exe from the build output (it usually connects to the database with write access).
