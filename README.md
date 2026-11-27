# claude-delphi

**A battle-tested toolkit of hooks, skills, agents, and zero-dependency Python tools to safely use [Claude Code](https://claude.com/claude-code) on legacy Delphi VCL & database codebases.**

[![tests](https://github.com/gsut/claude-delphi/actions/workflows/tests.yml/badge.svg)](https://github.com/gsut/claude-delphi/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Delphi 2007+](https://img.shields.io/badge/Delphi-2007%20--%2013-red.svg)](docs/installation.md#requirements)

🌐 **Languages:** English | [Türkçe](docs/tr/README.md)

---

## 💡 Why This Exists (Correctness Over Token Savings)

Using AI on a modern TypeScript or Python repo is easy. Using it on a **15-year-old Delphi VCL monolith**—with hundreds of units, ANSI (`cp1252` / `cp1254`) encodings, CRLF line endings, `.dfm` form bindings, and thousands of legacy compiler warnings—is a minefield.

> **Our core philosophy: Correctness is everything; saving tokens is nothing.**  
> On a legacy codebase, the most expensive thing isn't a long AI session—it's a subtle bug that compiles cleanly, looks plausible, and silently corrupts production data.

Every hook, guardrail, and sub-agent in this repository was forged over months of daily production work to force Claude Code to **measure before fixing, respect legacy file encodings, and audit its own work** before you ever run `git commit`.

*(Read the real-world story behind this workflow: [The Empty Twin Rows: Using Claude Code on a Legacy Delphi Code Base](https://medium.com/@gokhan.sut_29411/the-empty-twin-rows-using-claude-code-on-a-legacy-delphi-code-base-9d0f7fbd723a) or check out the [Case Study](docs/case-study.md).)*

---

## 🛡️ What Problems Does It Solve?

| The Legacy Delphi Trap | How `claude-delphi` Prevents It |
| :--- | :--- |
| **Encoding & Line-Ending Corruption:** AI saves `cp1252` / `cp1254` files as UTF-8 or turns `CRLF` into `LF`. | **`hooks/pascal_check.py`** — Right after each write, reports *new* encoding/LF violations (compared with the file as it was before the write) back to Claude. |
| **Destructive CLI Edits:** AI breaks files using `sed -i`, `>` redirections, or inline scripts. | **`hooks/command_guard.py`** & **`tools/pas_edit.py`** — Refuses the usual unsafe shell edits before they run (a pattern-based trip wire, see *Limits*) and provides a safe, encoding-aware Pascal/DFM editor. |
| **Accidental DB Writes:** AI connects to a database using an admin/write user. | **`hooks/command_guard.py`** — Refuses commands that name a write-enabled user (`psql`, `sqlcmd`, `mysql`, `isql` options, environment variables, connection strings). The real boundary is a read-only database user. |
| **Compiler Warning Blindness:** AI skips compiling or misses 2 new warnings buried inside 4,000 old ones. | **`build/build.bat` + `summary.py`** — Reports **errors and new warnings vs. baseline** (IDE-language independent; a failed build always shows as an error); `/build-check` makes "0 and 0" the acceptance rule. |
| **Broken DFM Bindings:** AI deletes a field or method thinking it's "unused", breaking a VCL form at runtime. | **`tools/dfm_field_check.py` & `dfm_field_usage.py`** — Maps `DataSource` and control bindings across `.dfm` files. |
| **False "Dead Code" Claims:** Simple `grep` misses nested routines, DFM events, or `{$IF}` blocks. | **`tools/pas_callers.py`** — A Pascal-aware reference finder that groups usages with evidence, and gives no "dead" verdict when something speaks against it (override / message methods, units outside the project). |
| **Blind Guessing on DB Side Effects:** AI guesses what a stored procedure or trigger touched. | **`tools/pg_fingerprint.py`** — Takes before/after row hashes across tables to prove database impact. |
| **Confirmation Bias in AI Reviews:** A sub-agent simply agrees with the main agent's plan. | **`/review` & `/multi-review` skills** — Before any code is written, context-free agents get only what will change, not the plan's conclusion, and count its scope / look for failure scenarios. |
| **Incomplete Implementations:** AI stops halfway or edits unrelated routines. | **`/close-out` + `tools/diff_routines.py`** — Maps every diff hunk to Pascal routines/DFM objects and lists what is not in the approved plan and what the plan names but nothing changed; an independent agent audits the rest. |
| **Binary DFMs:** Old forms saved in binary are unreadable for the AI and get corrupted by line-ending rules. | **`hooks/session_check.py`** + **`tools/dfm_text_check.py`** — Warns at the start of every new session and lists them; `pas_edit.py` refuses to touch one until you convert it to text. |
| **Repeating the Same Mistakes:** Your `CLAUDE.md` turns into an unreadable 2,000-line novel. | **`docs/mistake-log.md`** — A structured, concise log where every mistake becomes a **Rule + a Check you can see being done**; what a pattern can catch goes into a hook instead. |

---

## 🧠 The Workflow in 60 Seconds

1. **Triage (`/triage`):** Claude forms a hypothesis, gathers evidence and proposes a measurement that tells the
   hypotheses apart. **No code yet**; temporary measurement lines (`// X-MEASURE`) go in only after you approve.
2. **Plan & Approve:** Once measured, Claude writes a concrete plan to `personal/plans/<id>-plan.md` from a template (the
   tools read its plan items and scope; the agents use the other sections: callers left unchanged, removed calls).
3. **Blind Review (`/review` or `/multi-review`):** Before any code is written, context-free sub-agents (`scope-counter`,
   `devils-advocate`) get only what will change, not the plan's conclusion; findings are verified and logged.
4. **Surgical Execution:** Claude edits code safely via `pas_edit.py` (merging duplicate routines rather than copy-pasting fixes) and compiles against the baseline.
5. **Close-Out Audit (`/close-out`):** mechanical checks (`closeout_check.py`), a change map against the plan, and the
   `closeout-auditor` agent, which lists every difference between the diff and the approved plan. You review and commit.

---

## 🚀 Getting Started

Requirements, step-by-step installation, every setting in `claude-delphi.json`, localization, database notes and known
limits: **[docs/installation.md](docs/installation.md)**. Start with its first step — checking for binary DFMs.

---

## 📦 Repository Structure

```text
├── hooks/
│   ├── session_check.py      # SessionStart: Warns (through Claude) if the project has binary DFMs
│   ├── command_guard.py      # PreToolUse: Blocks sed -i, inline Python, DB write users, gh write commands, review-agent writes
│   └── pascal_check.py       # PostToolUse: Guards encoding (CP125x), CRLF, forbidden patterns, comment signatures, binary DFMs
├── build/
│   ├── build.bat             # MSBuild wrapper for Delphi (.dproj)
│   └── summary.py            # Compares compiler warnings/errors against your saved baseline
├── tools/                    # Zero-dependency Python CLI tools for Claude & developers
│   ├── pas_edit.py           # Safe, single-anchor Pascal/DFM editor with --reverse support
│   ├── pas_callers.py        # Finds all callers/references (code, {$IF}, DFM events, strings, comments)
│   ├── pascal_lex.py         # Lightweight Pascal lexer & routine boundary finder
│   ├── dfm_field_check.py    # Validates DFM control fields against dataset definitions
│   ├── dfm_field_usage.py    # Finds which DFM controls bind to specific database fields
│   ├── pg_fingerprint.py     # Before/after database record fingerprinter (PostgreSQL)
│   ├── diff_routines.py      # Maps git diff hunks to Pascal routines and DFM component chains
│   ├── closeout_check.py     # Mechanical close-out checks: measure lines, .bak, CreateForm, form registration, build age
│   └── dfm_text_check.py     # Lists binary DFMs that must be converted to text
├── .claude/
│   ├── skills/               # Custom workflows: /build-check, /triage, /review, /multi-review, /close-out
│   ├── agents/               # Specialized sub-agents: scope-counter, devils-advocate, closeout-auditor
│   └── templates/            # plan.md (section markers the tools read), reviews.md (review log, one row per round)
├── docs/
│   ├── installation.md       # Requirements, installation, settings, localization, databases, limits
│   ├── mistake-log.md        # Methodology, template, and 20 starter rules
│   ├── delphi-pitfalls.md    # 26 recurring Delphi VCL + SQL pitfalls
│   ├── build-baseline.md     # Deep dive into baseline warning management
│   ├── case-study.md         # Step-by-step walkthrough of a real bug hunt
│   └── tr/                   # Turkish documentation
├── examples/                 # Ready-to-use CLAUDE.md, settings.json, claude-delphi.json, gitattributes (copy as .gitattributes), and read-only SQL scripts
└── tests/                    # unittest suite for hooks, tools and build summary (Windows & Ubuntu)
```

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Changes: [CHANGELOG.md](CHANGELOG.md). License: [MIT](LICENSE).