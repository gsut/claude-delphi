"""Every reference to a routine (or any identifier) in a Delphi project, grouped so that a "dead code" verdict has evidence.

Usage:   python pas_callers.py --root <project dir> [--dpr <Project.dpr>] [--exclude <regex>] <Name | Class.Name>

Groups:
  definitions        where routines with this name are defined (file:line, nested path)
  code references    identifier uses outside comments and strings: calls, event assignments (OnClick := Name), ...
                     with the enclosing routine; uses inside the routine's own body are marked "self"
  other {$IF} branch uses in a non-first conditional compilation branch
  DFM bindings       <Property> = Name in .dfm files (OnClick, BeforeInsert, AfterPost, ...)
  name strings       'Name' inside string literals (FindComponent, MethodAddress, FieldByName, RTTI)
  comments           mentions in comments (not calls; listed so a commented-out call is not mistaken for a live one)
Files that are not part of the project (.dpr "in '...'" list) are marked "[not in .dpr]".

The "dead" verdict (with a ready evidence line) is given only when nothing speaks against it. No verdict when: a reference
is in a unit the .dpr does not list (search path, another project, a leftover copy: check whether it is compiled); the
routine is declared override / virtual / dynamic / message or is exported (the framework or another module calls it);
a .dpr unit lies outside --root (not searched); a file could not be parsed or a DFM is binary (not searched).

Limits: there is no type information. A reference "Obj.Name" is listed even if Obj belongs to another class with a
method of the same name; such references are marked with their qualifier for you to check. Code built from strings at
run time (other than literal names) cannot be found. Units outside --root that the .dpr does not list (other projects,
packages, a search path outside the root) are not searched.
"""
import argparse
import glob
import os
import re
import sys

sys.dont_write_bytecode = True   # no __pycache__ next to the tools in the user's project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pascal_lex as pl  # noqa: E402
from dfm_text_check import is_binary_dfm  # noqa: E402

NOT_A_NAME = {"begin", "var", "const", "type", "label", "asm"}      # "procedure begin ... end": an anonymous method
CALLED_BY_FRAMEWORK = {"override", "virtual", "dynamic", "message"}

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def read(path):
    raw = open(path, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", "replace")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")         # only ASCII identifiers are compared; any single-byte page is fine


def dpr_units(dpr, root):
    text = read(dpr)
    out = set()
    for m in re.finditer(r"\b[\w.]+\s+in\s+'([^']+)'", text, re.I):
        path = m.group(1).replace("\\", os.sep)   # .dpr paths are written with '\'; on Linux / macOS that is no separator
        out.add(os.path.normcase(os.path.normpath(os.path.join(os.path.dirname(dpr), path))))
    out.add(os.path.normcase(os.path.normpath(dpr)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--dpr", help="project file; default: the only .dpr in --root, if there is exactly one")
    ap.add_argument("--exclude", default=r"__history|__recovery|[\\/]backup[\\/]", help="regex of paths to skip")
    ap.add_argument("name")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    want = a.name.split(".")[-1].lower()
    qual = a.name.lower() if "." in a.name else None

    found = glob.glob(os.path.join(root, "*.dpr"))
    dpr = a.dpr or (found[0] if len(found) == 1 else None)
    members = dpr_units(dpr, root) if dpr else None

    files = [p for p in glob.glob(os.path.join(root, "**", "*.pas"), recursive=True)
             + glob.glob(os.path.join(root, "**", "*.dpr"), recursive=True)
             + glob.glob(os.path.join(root, "**", "*.inc"), recursive=True)
             if not re.search(a.exclude, p)]
    dfms = [p for p in glob.glob(os.path.join(root, "**", "*.dfm"), recursive=True) if not re.search(a.exclude, p)]

    def rel(p):
        r = os.path.relpath(p, root)
        if members is not None and p.lower().endswith((".pas", ".dpr")) and os.path.normcase(os.path.normpath(p)) not in members:
            r += " [not in .dpr]"
        return r

    defs, code, alt, strings, comments, failed, framework = [], [], [], [], [], [], []
    word = re.compile(r"\b%s\b" % re.escape(want), re.I)
    outside_root = sorted(m for m in (members or ()) if not os.path.normcase(m).startswith(os.path.normcase(root) + os.sep))
    for p in sorted(files):
        text = read(p)
        if want not in text.lower():
            continue
        try:
            toks = pl.tokenize(text, keep_comments=True)
            rs = pl.routines(text) if not p.lower().endswith(".inc") else []
        except pl.ParseError as e:
            failed.append("%s: %s" % (rel(p), e))
            continue
        own = [r for r in rs if r.short.lower() == want and (qual is None or r.name.lower() == qual
                                                              or r.name.lower().endswith("." + qual))]
        for r in own:
            defs.append("%s:%d  %s" % (rel(p), r.line, r.path()))
        header_until = -1
        for i, t in enumerate(toks):
            if t.kind == "comment":
                if word.search(t.text):
                    comments.append("%s:%d  %s" % (rel(p), t.line, t.text.strip()[:100]))
                continue
            if t.kind == "string":
                if word.search(t.text):
                    strings.append("%s:%d  %s" % (rel(p), t.line, t.text[:100]))
                continue
            if t.kind == "ident" and t.low in pl.ROUTINE_KW:
                j = i + 1
                while j < len(toks) and toks[j].kind == "comment":
                    j += 1
                # a header or a declaration, not a call; "procedure begin" is an anonymous method whose body is searched
                if j < len(toks) and toks[j].kind == "ident" and toks[j].low not in NOT_A_NAME:
                    depth, k = 0, j
                    while k < len(toks):
                        if toks[k].text == "(":
                            depth += 1
                        elif toks[k].text == ")":
                            depth -= 1
                        elif toks[k].text == ";" and depth == 0:
                            break
                        k += 1
                    header_until = toks[k].start if k < len(toks) else len(text)
                    names = [x.low for x in toks[j:k] if x.kind == "ident"]
                    if names[:3] and want in names[:3]:      # Name or Class.Name: the directives after the ';'
                        directives = []
                        m = k + 1
                        while m < min(len(toks), k + 20):
                            if toks[m].kind == "ident" and toks[m].low in pl.ROUTINE_KW | {"begin", "end", "var",
                                                                                         "const", "type"}:
                                break
                            if toks[m].kind == "ident":
                                directives.append(toks[m].low)
                            m += 1
                        hit = CALLED_BY_FRAMEWORK & set(directives)
                        if hit:
                            framework.append("%s:%d  %s" % (rel(p), toks[j].line, ", ".join(sorted(hit))))
                continue
            if t.kind != "ident" or t.low != want or t.start < header_until:
                continue
            prev = [x for x in toks[max(0, i - 3):i] if x.kind != "comment"]
            qualifier = prev[-2].text + "." if len(prev) >= 2 and prev[-1].text == "." and prev[-2].kind == "ident" else ""
            enc = pl.enclosing(rs, t.start)
            where = enc.path() if enc else "(unit level)"
            mark = "  self" if enc is not None and any(enc is r or _inside(enc, r) for r in own) else ""
            line = "%s:%d  in %s  %s%s%s" % (rel(p), t.line, where, qualifier, t.text, mark)
            (alt if t.alt else code).append(line)

    # any property whose value is the bare name: OnClick, BeforeInsert, AfterPost, OnFilterRecord ... (dataset events do not
    # start with "On"); a component reference with the same name would also be listed, with its property name
    events = []
    ev = re.compile(r"^\s*([\w.]+)\s*=\s*(\w+)\s*$", re.I)
    for p in sorted(dfms):
        with open(p, "rb") as f:
            if is_binary_dfm(f.read(512)):
                failed.append("%s: binary DFM, its event bindings cannot be read (convert it to text)" % rel(p))
                continue
        for n, s in enumerate(read(p).splitlines(), 1):
            m = ev.match(s)
            if m and m.group(2).lower() == want:
                events.append("%s:%d  %s = %s" % (rel(p), n, m.group(1), m.group(2)))

    def section(title, items):
        print("%s: %d" % (title, len(items)))
        for x in items:
            print("  " + x)

    print("name: %s   root: %s   project: %s" % (a.name, root, os.path.relpath(dpr, root) if dpr else "(no .dpr)"))
    section("definitions", defs)
    live = [c for c in code if not c.endswith("  self")]
    section("code references", code)
    section("other {$IF} branch", alt)
    section("DFM bindings", events)
    section("name strings", strings)
    section("comments (not calls)", comments)
    if failed:
        section("files that could not be parsed or read (not searched)", failed)
    if framework:
        section("declared override / virtual / dynamic / message (called by the framework)", framework)
    exported = [p for p in files if re.search(r"\bexports\b[^;]*\b%s\b" % re.escape(want), read(p), re.I | re.S)]
    if exported:
        section("exported (called from outside)", [rel(p) for p in exported])
    if outside_root:
        section(".dpr units outside --root (not searched)", [os.path.relpath(m, root) for m in outside_root[:10]]
                + (["... %d more" % (len(outside_root) - 10)] if len(outside_root) > 10 else []))
    in_project = [c for c in live if "[not in .dpr]" not in c]
    not_listed = [c for c in live if "[not in .dpr]" in c]
    if in_project or events or strings or alt:
        print("\nverdict: referenced (%d code, %d other branch, %d DFM, %d strings)"
              % (len(in_project), len(alt), len(events), len(strings)))
    elif not_listed or framework or exported or outside_root or failed:
        reasons = [x for x, on in (
            ("%d reference(s) in units the .dpr does not list - check whether they are compiled (search path, other "
             "projects) or leftover copies" % len(not_listed), not_listed),
            ("declared override / virtual / dynamic / message - the framework calls it", framework),
            ("exported - called from outside the project", exported),
            ("%d .dpr unit(s) outside --root were not searched" % len(outside_root), outside_root),
            ("%d file(s) could not be searched" % len(failed), failed)) if on]
        print("\nverdict: NO VERDICT - no reference in the searched project units, but:")
        for r in reasons:
            print("  - " + r)
        print("  Do not write a dead-code marker on this output; check the points above by hand.")
    else:
        print("\nverdict: no reference outside its own body in project units. Evidence for a dead-code marker:")
        print("  no callers: pas_callers.py %s -> 0 code references, 0 DFM bindings, 0 name strings%s"
              % (a.name, ", %d comment mention(s)" % len(comments) if comments else ""))


def _inside(r, outer):
    while r is not None:
        if r is outer:
            return True
        r = r.parent
    return False


if __name__ == "__main__":
    main()
