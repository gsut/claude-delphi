"""Every reference to a routine (or any identifier) in a Delphi project, grouped so that a "dead code" verdict has evidence.

Usage:   python pas_callers.py --root <project dir> [--dpr <Project.dpr>] <Name | Class.Name>

Groups:
  definitions        where routines with this name are defined (file:line, nested path)
  code references    identifier uses outside comments and strings: calls, event assignments (OnClick := Name), ...
                     with the enclosing routine; uses inside the routine's own body are marked "self"
  other {$IF} branch uses in a non-first conditional compilation branch
  DFM bindings       <Property> = Name in .dfm files (OnClick, BeforeInsert, AfterPost, ...)
  name strings       'Name' inside string literals (FindComponent, MethodAddress, FieldByName, RTTI)
  comments           mentions in comments (not calls; listed so a commented-out call is not mistaken for a live one)
Files that are not part of the project (.dpr "in '...'" list) are marked "[not in .dpr]".

Limits: there is no type information. A reference "Obj.Name" is listed even if Obj belongs to another class with a
method of the same name; such references are marked with their qualifier for you to check. Code built from strings at
run time (other than literal names) cannot be found.
"""
import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pascal_lex as pl  # noqa: E402

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
        out.add(os.path.normcase(os.path.normpath(os.path.join(os.path.dirname(dpr), m.group(1)))))
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

    defs, code, alt, strings, comments, failed = [], [], [], [], [], []
    word = re.compile(r"\b%s\b" % re.escape(want), re.I)
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
                if j < len(toks) and toks[j].kind == "ident":       # a header or a declaration, not a call
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
        section("files that could not be parsed (not searched)", failed)
    outside = [c for c in live if "[not in .dpr]" not in c]
    if not outside and not events and not strings and not alt and not failed:
        print("\nverdict: no reference outside its own body in project units. Evidence for a dead-code marker:")
        print("  no callers: pas_callers.py %s -> 0 code references, 0 DFM bindings, 0 name strings%s"
              % (a.name, ", %d comment mention(s)" % len(comments) if comments else ""))
    else:
        print("\nverdict: referenced (%d code, %d other branch, %d DFM, %d strings)"
              % (len(outside), len(alt), len(events), len(strings)))


def _inside(r, outer):
    while r is not None:
        if r is outer:
            return True
        r = r.parent
    return False


if __name__ == "__main__":
    main()
