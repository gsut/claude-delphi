# Command-line build and warning baseline

## Why

Before handing over a Pascal change, the AI should verify itself that it compiles and adds **no new** warnings. Legacy
projects have thousands of warnings and hints; "no warnings" is meaningless. The criterion is: **0 errors and 0 new
warnings / hints vs the baseline.** A new warning is either removed or justified in the report.

The build does not interfere with the developer's work: separate exe, separate dcu, separate log (`build\out\`,
`build\log\`).

## Layout

```
build\
  build.bat        msbuild wrapper (rsvars + configuration + output redirection + summary)
  summary.py       log summary: errors, warnings NEW vs baseline (language independent)
  out\exe\         Claude's exe (never run)
  out\dcu\
  log\last.log     full msbuild output of the last build
  log\baseline.txt warning baseline (key: file + code + message; no line number)
```

Committed: `build.bat`, `summary.py`, `log\baseline.txt`. `out\` and `log\last.log` go into `.gitignore`.

## Usage

```
cmd //c "build\build.bat"            build + compare with the baseline
cmd //c "build\build.bat" baseline   build + make this build's warnings the baseline
```

Sample output:

```
msbuild exit code: 0  errors: 0  warnings: 2221  hints: 4851
new warnings/hints vs baseline: 0
in baseline but no longer present: 52
```

**When to refresh the baseline:** on the first build after the developer's commit (the last commit changed and none of the
AI's own changes are in the working tree), or when the developer asks. Never while the AI's own change is on disk: that
would bury the new warnings in the baseline.

## Localized compilers

A German, French or Japanese Delphi (and a localized MSBuild) writes the kind of a message in its own language
("Warnung", "avertissement", ...). `summary.py` therefore never looks at the word: the kind comes from the code —
`E`/`F` error, `W` warning, `H` hint, and MSBuild `MSBnnnn` codes. Baseline keys contain the message text, so a baseline
taken with one IDE language does not match a build in another; take a new baseline after changing the IDE language.

## Pitfalls seen during setup

- The `.bat` file must have **CRLF** line endings; with LF, `cmd` swallows the start of lines (`'d' is not recognized`).
- If the project or path name contains non-ASCII characters, the script needs `chcp 65001`; otherwise
  `MSB1009: Project file does not exist`.
- `msbuild /clp:Summary` repeats every warning in the summary section and doubles the count. The script leaves it off.
- Library paths come from the IDE's `%APPDATA%\Embarcadero\BDS\<version>\EnvOptions.proj`; if a path changes in the IDE, the
  command-line build changes too.
- The command-line build reads files from disk. The IDE may compile an open data module from its in-memory copy; if a data
  module was changed outside the IDE, close and reopen the project there (the report says so).

## Reading diffs in Git

If the repository stores LF while the working tree uses CRLF (automatic conversion), a Pascal file rewritten by a script
shows as entirely changed in `git diff`. For the real difference use `git diff --ignore-cr-at-eol` (and `--stat`).

## Comparing with an old version (Git read-only)

The working tree is not changed (`checkout` / `stash` are blocked by the settings). If old source is needed:

```
mkdir -p build/old && git archive <rev> <path>/Unit.pas | tar -x -C build/old
mkdir -p build/old_source && git archive <rev> <folder> | tar -x -C build/old_source
```

`git show <rev>:<path>` is for reading on screen only: `hooks/command_guard.py` refuses a shell redirection into a `.pas`
file. Both folders belong in `.gitignore`.
