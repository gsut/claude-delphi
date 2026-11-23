# Contributing

This repository is shared as **examples and a method**. There is no support commitment, but contributions that make it
useful for more Delphi projects are welcome.

## Especially welcome

- **New pitfalls** for `docs/delphi-pitfalls.md` and **mistake log items** for `docs/mistake-log.md` — from real cases, in
  the existing format (symptom / root cause / how to catch it / fix pattern; or rule + check).
- **Translations** of the human-facing documents under `docs/<language>/` (see `docs/tr/` for the layout). Each translation
  starts with a note that the English version prevails.
- **Reports from other environments:** other Delphi versions, Win64, Linux, Community Edition, other databases.
- **Equivalents of the PostgreSQL examples** for SQL Server, MySQL / MariaDB or Firebird (tested ones only).

## Ground rules

- Skills, agents and hook messages stay in **English only**: Claude follows English instructions in any language, and
  translated copies of instructions drift apart. Localization is done through `claude-delphi.json` and one line in
  `CLAUDE.md` (see *Localization* in the README).
- **Standard library only** for Python code; Python 3.9+.
- Every change to a hook, a tool or `build/summary.py` comes with a test in `tests/`. Run the suite before opening a pull
  request:

  ```
  python -m unittest discover -s tests -v
  ```

- No customer data, company names, real database names or credentials — in code, docs, tests or commit messages.
- Keep changes surgical: one topic per pull request.

## Reporting a problem

Open an issue with the Delphi version, the operating system, the Python version, the command or tool input and the full
output. For a hook, include the JSON the hook received if you can.
