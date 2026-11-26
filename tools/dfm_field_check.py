"""DFM binding check: does every DataField / FieldName of a control or grid column bound to a DataSource exist as a
persistent field in that DataSource's dataset?

Usage: python dfm_field_check.py --root <project dir> [part of DataSource name ...]   (no part = all)
Limits: datasets without persistent fields are skipped; DataSources changed at run time (in code) are not visible.
Bindings of the form "Module.DsName" are resolved when the data module is another DFM.
"""
import argparse
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser()
ap.add_argument("--root", default=os.getcwd())
ap.add_argument("--exclude", default=r"__history|__recovery|/backup/", help="regex of paths to skip")
ap.add_argument("filter", nargs="*")
arg = ap.parse_args()
ROOT = os.path.abspath(arg.root).replace("\\", "/").rstrip("/") + "/"
FILTER = [a.lower() for a in arg.filter]
dfms = [p.replace("\\", "/") for p in glob.glob(ROOT + "**/*.dfm", recursive=True)
        if not re.search(arg.exclude, p.replace("\\", "/"))]


def objects(path):
    """Flat list of objects: name, class, indent, property lines (children excluded), parent."""
    lines = open(path, "rb").read().decode("latin-1").splitlines()
    out, stack = [], []
    for s in lines:
        m = re.match(r"^(\s*)(object|inherited|inline)\s+(\w+)\s*:\s*(\w+)", s)
        if m:
            o = {"name": m.group(3), "cls": m.group(4), "ind": len(m.group(1)), "props": [], "parent": stack[-1] if stack else None}
            out.append(o)
            stack.append(o)
            continue
        if stack and re.match(r"^\s*end\s*$", s) and len(s) - len(s.lstrip()) == stack[-1]["ind"]:
            stack.pop()
            continue
        if stack:
            stack[-1]["props"].append(s.strip())
    return out


modules = {}  # form / module name -> (path, objects)
for p in dfms:
    objs = objects(p)
    if objs:
        modules[objs[0]["name"].lower()] = (p, objs)

# dataset fields and DataSource -> dataset (TDataSource and any component class ending in "DataSource")
fields, source = {}, {}
for mod, (p, objs) in modules.items():
    for o in objs:
        fn = [re.match(r"FieldName = '(.*)'", x).group(1).lower() for x in o["props"] if re.match(r"FieldName = '", x)]
        if fn and o["parent"] is not None and o["cls"].lower().endswith("field"):
            fields.setdefault((mod, o["parent"]["name"].lower()), set()).add(fn[0])
        if o["cls"].lower().endswith("datasource"):
            ds = [x.split("=")[1].strip() for x in o["props"] if x.startswith("DataSet =")]
            if ds:
                d = ds[0].lower()
                source[(mod, o["name"].lower())] = tuple(d.split(".")) if "." in d else (mod, d)

missing = checked = 0
for mod, (p, objs) in modules.items():
    for o in objs:
        src = [x.split("=")[1].strip() for x in o["props"] if re.match(r"(DataBinding\.)?DataSource =", x)]
        if not src:
            continue
        s = src[0].lower()
        k = tuple(s.split(".")) if "." in s else (mod, s)
        if FILTER and not any(x in s for x in FILTER):
            continue
        ds = source.get(k)
        if ds is None or ds not in fields:
            continue
        for x in o["props"]:
            m = re.match(r"(DataBinding\.DataField|DataField|FieldName) = '(.*)'", x)
            if not m:
                continue
            for f in m.group(2).split(";"):
                checked += 1
                if f.lower() not in fields[ds]:
                    missing += 1
                    print(f'MISSING  {os.path.relpath(p, ROOT)}: {o["name"]} ({o["cls"]}) {m.group(1)} = {f}  ->  {src[0]} / {ds[1]}')
print(f"{checked} bindings checked, {missing} missing fields")
sys.exit(1 if missing else 0)
