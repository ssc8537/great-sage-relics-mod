"""Find every PBTable record anywhere that references item id 4096 (or the other relics)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak  # noqa: E402
import pb  # noqa: E402

P = r"C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks"
IDS = {4091, 4092, 4093, 4094, 4095, 4096}
p = pak.Pak(os.path.join(P, "pakchunk16-Windows.pak"))
rels = sorted(k for k in p.files if "PBTable" in k)
out = []


def scan_fields(fields, rel, depth=0):
    for f in fields:
        if f["wire"] == 0 and f.get("value") in IDS:
            out.append("%s  field#%d = %d" % (rel, f["no"], f["value"]))
        if f["wire"] == 2 and f.get("sub") and depth < 2:
            scan_fields(f["sub"], rel, depth + 1)


for rel in rels:
    data = p.read(rel)
    try:
        for rec in pb.parse(data):
            if rec["no"] == 1 and rec["wire"] == 2:
                try:
                    scan_fields(pb.parse(rec["raw"]), rel)
                except Exception:
                    pass
    except Exception as e:
        out.append("ERR %s %s" % (rel, e))

seen = []
for line in out:
    if line not in seen:
        seen.append(line)
for line in seen:
    print(line)
print("total distinct refs:", len(seen))
