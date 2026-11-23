"""Fingerprint of all rows belonging to one record (e.g. one customer file / tenant) across all tables; before / after diff.
Answers "what else did this screen or operation touch?" by taking a fingerprint before and after running the program.

Usage:
  python pg_fingerprint.py take <key value> <out.json> [--key-column tenant_id] [--group-column period] [--table-pattern ...]
  python pg_fingerprint.py diff <before.json> <after.json>

Connects through psql using PGHOST / PGPORT / PGUSER / PGDATABASE and .pgpass (or PGPASSFILE). Use a READ-ONLY user.
Row contents are never written to the file: only the row identity (id or ctid), the group column and an md5 of the content.
The md5 is taken without the 'id' column, so a row deleted and re-inserted with the same content shows as "same content".
"""
import argparse
import json
import os
import subprocess
from collections import Counter

PSQL = os.environ.get("PSQL", "psql")


def query(sql):
    r = subprocess.run([PSQL, "-w", "-At", "-F", chr(9), "-c", sql], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return [s.split(chr(9)) for s in r.stdout.splitlines() if s]


def tables(keys, groups, pattern):
    # tables having a key column; plus whether they have a group column and an id
    cols = keys + groups + ["id"]
    rows = query("select table_name, string_agg(column_name, ',') from information_schema.columns "
                 "where table_schema = 'public' and table_name ~ '%s' and column_name in (%s) group by 1 order by 1"
                 % (pattern.replace("'", "''"), ",".join("'%s'" % c for c in cols)))
    out = []
    for t, c in rows:
        c = c.split(",")
        key = next((k for k in keys if k in c), None)
        if key:
            group = next((g for g in groups if g in c), None)
            out.append((t, key, group, "id" in c))
    return out


def take(value, out_path, keys, groups, pattern):
    v = value.replace("'", "''")
    result = {}
    for t, key, group, has_id in tables(keys, groups, pattern):
        gx = ("coalesce(%s::text, '')" % group) if group else "''"
        idx = "id::text" if has_id else "ctid::text"
        # alias zz_row: a short alias such as 't' can collide with a column of the same name (to_jsonb would take the column)
        rows = query("select %s, %s, md5((to_jsonb(zz_row) - 'id')::text) from %s zz_row where trim(%s::text) = '%s'"
                     % (idx, gx, t, key, v))
        if rows:
            result[t] = {r[0]: [r[1], r[2]] for r in rows}
    json.dump(result, open(out_path, "w", encoding="utf-8"))
    print(value, "tables", len(result), "rows", sum(len(x) for x in result.values()))


def diff(a, b):
    A = json.load(open(a, encoding="utf-8"))
    B = json.load(open(b, encoding="utf-8"))

    def by_group(ids, src):
        return dict(sorted(Counter(src[i][0] or "-" for i in ids).items()))

    def content_by_group(c):
        d = Counter()
        for (g, _), n in c.items():
            d[g or "-"] += n
        return dict(sorted(d.items()))

    for t in sorted(set(A) | set(B)):
        x, y = A.get(t, {}), B.get(t, {})
        deleted = [i for i in x if i not in y]
        added = [i for i in y if i not in x]
        changed = [i for i in x if i in y and x[i][1] != y[i][1]]
        if deleted or added or changed:
            print("%-12s changed %4d %s  added %4d %s  deleted %4d %s" % (
                t, len(changed), by_group(changed, y), len(added), by_group(added, y), len(deleted), by_group(deleted, x)))
            # content comparison (independent of id): per group, content only before / only after
            ca = Counter((v[0], v[1]) for v in x.values())
            cb = Counter((v[0], v[1]) for v in y.values())
            print("%-12s   content: only before %s  only after %s" % ("", content_by_group(ca - cb), content_by_group(cb - ca)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["take", "diff"])
    ap.add_argument("first")
    ap.add_argument("second")
    ap.add_argument("--key-column", action="append", help="column selecting the record (repeatable; first one found is used)")
    ap.add_argument("--group-column", action="append", help="column grouping the results (e.g. period, version)")
    ap.add_argument("--table-pattern", default=".*")
    a = ap.parse_args()
    if a.action == "take":
        take(a.first, a.second, a.key_column or ["tenant_id"], a.group_column or [], a.table_pattern)
    else:
        diff(a.first, a.second)
