"""Small Object Pascal lexer and routine finder, shared by pas_edit.py, pas_callers.py and diff_routines.py.

Not a compiler: it separates comments, strings and identifiers, and finds where every routine (including nested
routines, class methods, operators, generic methods) starts and ends by matching begin / end. When the structure is
not what it expects it raises ParseError instead of guessing, so callers can refuse to act.

Conditional compilation: in {$IF...} / {$IFDEF} / {$IFNDEF} / {$IFOPT} ... {$ELSE} / {$ELSEIF} ... {$ENDIF} / {$IFEND}
(also written (*$IFDEF ...*)) only the first branch is used to find routine boundaries (each branch is expected to be
balanced on its own). Tokens of the other branches are still returned, marked alt=True, so a search for calls does not
miss them. Reading stops at the unit's final "end." (the compiler ignores anything after it).

Handled: cracker / exception classes without a body (TX = class(TBase);), generic constraints (<T: record>), attributes
before a header ([Test]), nested generic class names (TFoo<TPair<K, V>>.Bar), "end" used as a name (Range.End[xlUp],
asm label @@end), inline record variables (var R: record ... end;). Checked against 704 units of a real project: 698
unchanged, 6 gained routines the previous version dropped silently, none lost.

Known limits: local class / interface type declarations inside a routine are skipped with a simple depth count; include
files ({$I ...}) are not expanded; a routine whose body is in an include file, and Delphi 12 multi-line ''' strings,
raise ParseError.
"""
import re

ROUTINE_KW = {"procedure", "function", "constructor", "destructor", "operator"}
BLOCK_OPEN = {"begin", "case", "try", "asm"}
DIRECTIVES = {
    "overload", "override", "virtual", "dynamic", "abstract", "reintroduce", "static", "inline", "assembler",
    "cdecl", "stdcall", "safecall", "register", "pascal", "winapi", "varargs", "message", "deprecated", "platform",
    "library", "experimental", "final", "dispid", "export", "local", "near", "far", "unsafe", "forward", "external",
}
NO_BODY = {"forward", "external"}


class ParseError(Exception):
    pass


class Token:
    __slots__ = ("kind", "text", "low", "start", "end", "line", "alt")

    def __init__(self, kind, text, start, end, line, alt=False):
        self.kind, self.text, self.start, self.end, self.line, self.alt = kind, text, start, end, line, alt
        self.low = text.lower() if kind == "ident" else text

    def __repr__(self):
        return "%s(%r@%d)" % (self.kind, self.text, self.line)


_IDENT = re.compile(r"&?[A-Za-z_][A-Za-z0-9_]*")
_NUMBER = re.compile(r"\$[0-9A-Fa-f]+|%[01]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


_COND = re.compile(r"(?:\{|\(\*)\$(IFDEF|IFNDEF|IFOPT|IF|ELSEIF|ELSE|ENDIF|IFEND)\b", re.I)   # {$IF..} and (*$IF..*)


def _conditional(m, cond):
    d = m.group(1).upper()
    if d in ("IFDEF", "IFNDEF", "IFOPT", "IF"):
        cond.append(False)
    elif d in ("ELSE", "ELSEIF") and cond:
        cond[-1] = True
    elif d in ("ENDIF", "IFEND") and cond:
        cond.pop()


def tokenize(text, keep_comments=False):
    """Returns tokens of kind ident / string / number / symbol (and comment if keep_comments)."""
    toks, i, n, line = [], 0, len(text), 1
    cond = []                                     # per open {$IF}: True once the first branch has ended
    _append = toks.append

    def emit(tok):
        tok.alt = any(cond)
        _append(tok)

    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if c in " \t\r\f\v\x00":
            i += 1
            continue
        start, sline = i, line
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            if keep_comments:
                emit(Token("comment", text[i:j], i, j, sline))
            i = j
            continue
        if c == "{":
            j = text.find("}", i + 1)
            if j < 0:
                raise ParseError("unterminated { comment at line %d" % sline)
            line += text.count("\n", i, j)
            m = _COND.match(text, i)
            if m:
                _conditional(m, cond)
            if keep_comments:
                emit(Token("comment", text[i:j + 1], i, j + 1, sline))
            i = j + 1
            continue
        if text.startswith("(*", i):
            j = text.find("*)", i + 2)
            if j < 0:
                raise ParseError("unterminated (* comment at line %d" % sline)
            line += text.count("\n", i, j)
            m = _COND.match(text, i)
            if m:
                _conditional(m, cond)
            if keep_comments:
                emit(Token("comment", text[i:j + 2], i, j + 2, sline))
            i = j + 2
            continue
        if c == "'":
            j = i + 1
            while True:
                k = text.find("'", j)
                if k < 0 or text.find("\n", j, k) >= 0:
                    raise ParseError("unterminated string at line %d" % sline)
                if k + 1 < n and text[k + 1] == "'":
                    j = k + 2
                    continue
                break
            emit(Token("string", text[i:k + 1], i, k + 1, sline))
            i = k + 1
            continue
        m = _IDENT.match(text, i)
        if m:
            emit(Token("ident", m.group(0).lstrip("&"), i, m.end(), sline))
            i = m.end()
            # "end." closes the unit: the compiler ignores the rest of the file
            if m.group(0).lower() == "end" and not cond:
                k = i
                while k < n and text[k] in " \t\r\n":
                    k += 1
                if k < n and text[k] == "." and text[k + 1:k + 2] != ".":
                    emit(Token("symbol", ".", k, k + 1, line + text.count("\n", i, k)))
                    break
            continue
        m = _NUMBER.match(text, i)
        if m and m.end() > i:
            emit(Token("number", m.group(0), i, m.end(), sline))
            i = m.end()
            continue
        if c == "#":
            m = re.compile(r"#(\$[0-9A-Fa-f]+|\d+)").match(text, i)
            if m:
                emit(Token("string", m.group(0), i, m.end(), sline))
                i = m.end()
                continue
        two = text[i:i + 2]
        if two in (":=", "<=", ">=", "<>", "..", "+=", "-="):
            emit(Token("symbol", two, i, i + 2, sline))
            i += 2
            continue
        emit(Token("symbol", c, i, i + 1, sline))
        i += 1
    return toks


class Routine:
    def __init__(self, name, kind, start_tok, parent):
        self.name, self.kind, self.parent = name, kind, parent
        self.start, self.line = start_tok.start, start_tok.line
        self.end = self.end_line = None
        self.body_start = None        # offset of the routine's own 'begin' / 'asm'
        self.children = []

    @property
    def short(self):
        return self.name.split(".")[-1]

    def path(self):
        p, r = [], self
        while r:
            p.append(r.name)
            r = r.parent
        return " > ".join(reversed(p))

    def __repr__(self):
        return "Routine(%s, lines %d-%s)" % (self.path(), self.line, self.end_line)


def _is_header(toks, i):
    """toks[i] is a routine keyword that starts a routine header (not a procedural type or an anonymous method)."""
    if toks[i].low not in ROUTINE_KW or i + 1 >= len(toks) or toks[i + 1].kind != "ident":
        return False
    j = i - 1
    if j >= 0 and toks[j].low == "class":
        j -= 1
    # "]" closes an attribute written before the header: [Test] procedure ...
    return j < 0 or toks[j].text in (";", "]") or toks[j].low in ("implementation", "private", "public", "protected",
                                                                  "published", "strict")


def _not_keyword(toks, j):
    """toks[j] is used as a name, not as a keyword: after '.' (Range.End[xlUp]) or '@' (an asm label @@end)"""
    return j > 0 and toks[j - 1].text in (".", "@")


def _opens_type_body(toks, j):
    """toks[j] starts a type body closed by 'end': record, object (not 'of object'), class / interface after '='."""
    t, prev = toks[j], toks[j - 1].low if j > 0 else ""
    if t.kind != "ident" or _not_keyword(toks, j):
        return False
    if t.low == "record":
        # a generic constraint <T: record> / <T: record, constructor> has no body
        return not (j + 1 < len(toks) and toks[j + 1].text in (">", ","))
    if t.low == "object":
        return prev != "of"
    return t.low in ("class", "interface") and prev == "="


def _skip_type_body(toks, i):
    """toks[i] is record / class / object / interface after '='; returns index after its closing 'end'."""
    nxt = toks[i + 1] if i + 1 < len(toks) else None
    if toks[i].low in ("class", "interface") and nxt is not None and (nxt.text == ";" or nxt.low == "of"):
        return i + 1                              # forward declaration or class of
    if toks[i].low in ("class", "interface") and nxt is not None and nxt.text == "(":
        k, depth = i + 1, 0                       # EMy = class(Exception); has no body
        while k < len(toks):
            if toks[k].text == "(":
                depth += 1
            elif toks[k].text == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        if k + 1 < len(toks) and toks[k + 1].text == ";":
            return k + 1
    depth, j = 1, i + 1
    while j < len(toks):
        t = toks[j]
        if _opens_type_body(toks, j):
            depth += 1
        elif t.low == "end" and not _not_keyword(toks, j):
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    raise ParseError("type declaration starting at line %d is not closed" % toks[i].line)


def _parse_routine(toks, i, parent, out):
    kw = toks[i]
    j = i + 1
    name = [toks[j].text]
    j += 1
    while j < len(toks):                          # qualified / generic name: TFoo<T>.Bar
        if toks[j].text == "." and j + 1 < len(toks) and toks[j + 1].kind == "ident":
            name.append(toks[j + 1].text)
            j += 2
        elif toks[j].text == "<":
            k, depth = j, 0                       # nested type arguments: TFoo<TPair<K, V>>.Bar
            while k < len(toks):
                if toks[k].text == "<":
                    depth += 1
                elif toks[k].text == ">":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            j = k + 1
        else:
            break
    r = Routine(".".join(name), kw.low, kw, parent)
    depth = 0                                     # parameter list may contain ';'
    while j < len(toks):
        t = toks[j]
        if t.text == "(":
            depth += 1
        elif t.text == ")":
            depth -= 1
        elif t.text == ";" and depth == 0:
            break
        j += 1
    j += 1
    no_body = False
    while j < len(toks) and toks[j].kind == "ident" and toks[j].low in DIRECTIVES:
        no_body = no_body or toks[j].low in NO_BODY
        while j < len(toks) and toks[j].text != ";":
            j += 1
        j += 1
    if no_body:
        r.end, r.end_line = toks[j - 1].end, toks[j - 1].line
        out.append(r)
        return j, r
    # declaration part: var / const / type / nested routines, until the routine's own begin / asm
    while j < len(toks):
        t = toks[j]
        if t.kind == "ident" and _is_header(toks, j):
            j, child = _parse_routine(toks, j, r, out)
            r.children.append(child)
            continue
        if _opens_type_body(toks, j):
            j = _skip_type_body(toks, j)
            continue
        if t.low in ("begin", "asm"):
            r.body_start = t.start
            d = 0
            while j < len(toks):
                u = toks[j]
                if u.kind == "ident" and not _not_keyword(toks, j):
                    # an inline variable of a record type (var R: record ... end;) closes with its own end
                    if u.low in BLOCK_OPEN or (u.low == "record" and _opens_type_body(toks, j)):
                        d += 1
                    elif u.low == "end":
                        d -= 1
                        if d == 0:
                            k = j + 1 if j + 1 < len(toks) and toks[j + 1].text == ";" else j
                            r.end, r.end_line = toks[k].end, toks[k].line
                            out.append(r)
                            return k + 1, r
                j += 1
            raise ParseError("routine %s starting at line %d has no matching end" % (r.name, r.line))
        if t.low in ("implementation", "initialization", "finalization"):
            raise ParseError("routine %s starting at line %d has no body before '%s' (line %d)"
                             % (r.name, r.line, t.text, t.line))
        j += 1
    raise ParseError("routine %s starting at line %d reaches end of file" % (r.name, r.line))


def routines(text):
    """All routines with bodies or forward / external declarations in the implementation part (whole file for
    programs / .dpr). Nested routines are included, with .parent set."""
    toks = [t for t in tokenize(text) if not t.alt]
    start = 0
    for k, t in enumerate(toks):
        if t.low == "implementation":
            start = k + 1
            break
    out, j = [], start
    while j < len(toks):
        t = toks[j]
        if t.kind == "ident" and t.low in ("initialization", "finalization"):
            break
        if t.kind == "ident" and _is_header(toks, j):
            j, _ = _parse_routine(toks, j, None, out)
            continue
        if _opens_type_body(toks, j):
            j = _skip_type_body(toks, j)
            continue
        j += 1
    return sorted(out, key=lambda r: r.start)


def find_routine(rs, name):
    """Routines matching name: 'TForm1.Button1Click', 'Button1Click' or a nested path 'Outer > Inner' (case-insensitive)."""
    n = name.lower().replace(" ", "")
    if ">" in n:
        return [r for r in rs if r.path().lower().replace(" ", "") == n]
    return [r for r in rs if r.name.lower() == n or r.short.lower() == n]


def enclosing(rs, offset):
    """The innermost routine containing the offset, or None."""
    best = None
    for r in rs:
        if r.end is not None and r.start <= offset < r.end and (best is None or r.start >= best.start):
            best = r
    return best
