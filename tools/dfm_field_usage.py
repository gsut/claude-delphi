"""Lists the DFM controls bound to the given field names (DataField / FieldName), with the DataSource of the same object.
Answers "is this field shown anywhere on screen?" - use it next to a Pascal search when proving a field or code is dead.

Usage:   python dfm_field_usage.py --root <project dir> <DataSource regex> <field1> [field2 ...]
Example: python dfm_field_usage.py --root . "DmMain\\.DsCustomer$" Name OldCode
Positive control: also pass a field you know is bound on screen; if it is not listed, the pattern is wrong.
"""
import argparse
import os
import re

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=os.getcwd())
ap.add_argument("--exclude", default=r"__history|__recovery", help="regex of folders to skip")
ap.add_argument("datasource")
ap.add_argument("fields", nargs="+")
arg = ap.parse_args()
ds_pattern = re.compile(arg.datasource, re.I)
wanted = {f.lower() for f in arg.fields}
for folder, dirs, files in os.walk(arg.root):
    if re.search(arg.exclude, folder):
        continue
    for name in files:
        if not name.lower().endswith(".dfm"):
            continue
        path = os.path.join(folder, name)
        lines = open(path, encoding="latin-1").read().splitlines()
        stack = []  # per level: [object line, datasource, [(line no, field)]]
        for i, s in enumerate(lines, 1):
            t = s.strip()
            if re.match(r"(object|inherited|inline) ", t):
                stack.append([t, None, []])
            elif t == "end" and stack:
                obj, ds, hits = stack.pop()
                for no, field in hits:
                    if ds and ds_pattern.search(ds):
                        print("%s:%d  %s  DataSource=%s  field=%s" % (os.path.relpath(path, arg.root), no, obj, ds, field))
            elif stack:
                m = re.match(r"DataSource\s*=\s*(\S+)", t)
                if m:
                    stack[-1][1] = m.group(1)
                m = re.match(r"(DataField|FieldName)\s*=\s*'([^']*)'", t)
                if m and m.group(2).lower() in wanted:
                    stack[-1][2].append((i, m.group(2)))
