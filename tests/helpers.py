"""Shared helpers for the tests (standard library only: run with  python -m unittest discover -s tests -v)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, "hooks")
TOOLS = os.path.join(ROOT, "tools")
BUILD = os.path.join(ROOT, "build")

# A unit that exercises the parser: two routines with the same anchor, a nested routine, an {$IFDEF} branch with its own
# begin / end, a local "of object" type, a local record, an anonymous method, a case statement and text after "end.".
SAMPLE_PAS = (
    "unit Sample;\n"
    "\n"
    "interface\n"
    "\n"
    "type\n"
    "  TForm1 = class(TObject)\n"
    "    procedure First;\n"
    "    procedure Second;\n"
    "  end;\n"
    "\n"
    "implementation\n"
    "\n"
    "procedure TForm1.First;\n"
    "type\n"
    "  TProc = procedure(Sender: TObject) of object;\n"
    "  TRec = record\n"
    "    A: Integer;\n"
    "  end;\n"
    "var\n"
    "  X: Integer;\n"
    "\n"
    "function Inner(N: Integer): Integer;\n"
    "begin\n"
    "  Result := N * 2;\n"
    "end;\n"
    "\n"
    "begin\n"
    "  X := 0;\n"
    "  {$IFDEF FPC}\n"
    "  if X = 0 then\n"
    "  begin\n"
    "  {$ELSE}\n"
    "  if X = 1 then\n"
    "  begin\n"
    "  {$ENDIF}\n"
    "    X := Inner(X);\n"
    "  end;\n"
    "  case X of\n"
    "    0: X := 1;\n"
    "  end;\n"
    "  Result := False; // Ölçüm\n"
    "end;\n"
    "\n"
    "procedure TForm1.Second;\n"
    "var\n"
    "  P: TProc<Integer>;\n"
    "begin\n"
    "  P := procedure(I: Integer)\n"
    "    begin\n"
    "      Writeln(I);\n"
    "    end;\n"
    "  try\n"
    "    First;\n"
    "  finally\n"
    "    Result := False; // Ölçüm\n"
    "  end;\n"
    "  Result := False; // Ölçüm\n"
    "end;\n"
    "\n"
    "end.\n"
    "Anything after the final end. is ignored by the compiler: 'unterminated\n"
)


# A binary DFM as the IDE writes it: a resource header (FF, type 0A 00, name, flags, size) followed by the "TPF0" stream.
BINARY_DFM = (b"\xff\x0a\x00TFORM1\x00\x30\x10" + (19).to_bytes(4, "little") + b"TPF0\x06TForm1\x05Form1\x00\x00")
TEXT_DFM = b"object Form1: TForm1\r\n  Caption = 'Form'\r\nend\r\n"


def write_sample(folder, name="Sample.pas", text=SAMPLE_PAS, encoding="cp1254", crlf=True):
    path = os.path.join(folder, name)
    data = text.replace("\n", "\r\n") if crlf else text
    with open(path, "wb") as f:
        f.write(data.encode(encoding))
    return path


class TempProject:
    """A temporary project folder with .claude/claude-delphi.json; optional git repository."""

    def __init__(self, settings=None, git=False):
        self.dir = tempfile.mkdtemp(prefix="claude-delphi-test-")
        os.makedirs(os.path.join(self.dir, ".claude"))
        with open(os.path.join(self.dir, ".claude", "claude-delphi.json"), "w", encoding="utf-8") as f:
            json.dump(settings or {}, f)
        if git:
            subprocess.run(["git", "init", "-q"], cwd=self.dir, check=True)

    def env(self):
        return dict(os.environ, CLAUDE_PROJECT_DIR=self.dir, PYTHONIOENCODING="utf-8")

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def run_hook(name, payload, project, raw=None):
    """Runs a hook the way Claude Code does: JSON on stdin as raw UTF-8 (non-ASCII characters not escaped). A hook that
    crashes or writes to stderr fails the test: a silent crash must never pass as "silent = allowed"."""
    data = raw if raw is not None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    r = subprocess.run([sys.executable, "-I", os.path.join(HOOKS, name)], input=data, capture_output=True,
                       env=project.env(), cwd=project.dir)
    if r.returncode != 0 or r.stderr.strip():
        raise AssertionError("hook %s failed: exit %d, stderr: %s" % (name, r.returncode,
                                                                     r.stderr.decode("utf-8", "replace")))
    out = r.stdout.decode("utf-8")
    return json.loads(out) if out.strip() else None


def run_tool(path, args, project=None):
    env = project.env() if project else dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, path] + list(args), capture_output=True, text=True, encoding="utf-8", env=env)
