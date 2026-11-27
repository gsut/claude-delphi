"""Shared by the hooks; copied together with them to .claude/hooks/ (the hooks import it from their own folder).

- load_settings: .claude/claude-delphi.json, read as UTF-8 with or without a BOM (Notepad and PowerShell 5.1 write one).
  A missing file means the defaults; a file that exists but cannot be read is reported to the caller, never swallowed:
  a silent fall back to the defaults switched rules off (e.g. an empty write_db_users).
- read_input: the hook input JSON from stdin as UTF-8 bytes. Under `python -I` stdin is decoded in the console code page,
  which garbles non-ASCII paths (C:\\Users\\Gökhan\\...) so the hook would silently check nothing.
"""
import json
import os
import sys

SETTINGS_FILE = os.path.join(".claude", "claude-delphi.json")


def project_root():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def load_settings(defaults, root=None):
    """(settings, problem): the defaults updated from the settings file; problem is None, or a sentence saying why the
    file could not be used (the defaults then apply and the caller must make that visible)."""
    s = dict(defaults)
    path = os.path.join(root or project_root(), SETTINGS_FILE)
    if not os.path.exists(path):
        return s, None
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("not a JSON object")
    except (OSError, ValueError) as e:
        return s, "%s cannot be read (%s: %s); fix it - until then the built-in defaults apply" % (
            path, type(e).__name__, e)
    s.update(data)
    return s, None


def read_input():
    """the hook input as a dict; raises ValueError (also for bytes that are not UTF-8) if it is not a JSON object"""
    raw = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
    data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("hook input is not a JSON object")
    return data
