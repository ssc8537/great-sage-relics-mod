"""Find every table/record that references a given set of numeric ids (drop-rule ids etc.)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak  # noqa: E402
import pb  # noqa: E402

P = r"C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks"
TARGETS = {int(x) for x in (sys.argv[1:] or
                            ["1030", "10105", "9901", "9906", "9999", "9000"])}
p = pak.Pak(os.path.join(P, "pakchunk16-Windows.pak"))
rels = sorted(k for k in p.files if "PBTable" in k)
found = {t: [] for t in TARGETS}


def walk(fields, rel, key, depth=0):
    for f in fields:
        if f["wire"] == 0 and f.get("value") in TARGETS:
            found[f["value"]].append("%s  rec=%s field#%d" % (rel, key, f["no"]))
        if f["wire"] == 2 and f.get("sub") and depth < 3:
            walk(f["sub"], rel, key, depth + 1)


for rel in rels:
    try:
        data = p.read(rel)
    except Exception:
        continue
    if not rel.endswith(".data"):
        continue
    try:
        recs = pb.parse(data)
    except Exception:
        continue
    for rec in recs:
        if rec["no"] == 1 and rec["wire"] == 2:
            try:
                fs = pb.parse(rec["raw"])
            except Exception:
                continue
            key = fs[0].get("value") if fs and fs[0]["wire"] == 0 else "?"
            walk(fs, rel, key)

for t in sorted(TARGETS):
    hits = found[t]
    print("### id %s : %d hits" % (t, len(hits)))
    for h in hits[:40]:
        print("     ", h)
