"""Scan every PBTable for records whose first varint field is a relic item/group id."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak  # noqa: E402
import pb  # noqa: E402

GAME_PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks"
IDS = set(range(4091, 4097))

p = pak.Pak(os.path.join(GAME_PAKS, "pakchunk16-Windows.pak"))
rels = sorted(k for k in p.files if "PBTable" in k)
out = []
for rel in rels:
    data = p.read(rel)
    try:
        recs = [f["raw"] for f in pb.parse(data) if f["no"] == 1 and f["wire"] == 2]
    except Exception:
        continue
    hit_ids = []
    for raw in recs:
        try:
            fs = pb.parse(raw)
        except Exception:
            continue
        if fs and fs[0]["wire"] == 0 and fs[0].get("value") in IDS:
            hit_ids.append(fs[0]["value"])
    if hit_ids:
        out.append("%s : %d/%d records, ids=%s" % (rel, len(hit_ids), len(recs),
                                                   sorted(set(hit_ids))))
for line in out:
    print(line)
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  "work", "analysis", "relic_id_scan.txt"), "w",
     encoding="utf-8").write("\n".join(out))
print("total tables with relic-id records:", len(out))
