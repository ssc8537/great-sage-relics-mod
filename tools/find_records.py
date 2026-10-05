"""Find records in a PBTable whose fields contain any of the given UTF-8 strings."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak  # noqa: E402
import pb  # noqa: E402

GAME_PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks"
NEEDLES = [s.encode("utf-8") for s in (sys.argv[2:] or ["意见欲"])]
REL = sys.argv[1]

p = pak.Pak(os.path.join(GAME_PAKS, "pakchunk16-Windows.pak"))
data = p.read(REL)


def walk(fields, raw, path=""):
    for f in fields:
        if f["wire"] == 2 and f.get("raw") and any(n in f["raw"] for n in NEEDLES):
            yield f


hits = []
for rec in pb.parse(data):
    if rec["no"] == 1 and rec["wire"] == 2:
        if any(n in rec["raw"] for n in NEEDLES):
            hits.append(rec["raw"])

print("records containing needles:", len(hits))
out = []
for raw in hits:
    out.append("=" * 60)
    for f in pb.parse(raw):
        t = f.get("text")
        if t is not None:
            val = repr(t)
        elif f["wire"] == 2:
            val = "bytes " + f["raw"][:40].hex()
        else:
            val = str(f.get("value"))
        out.append("   f%-3d w%d %s" % (f["no"], f["wire"], val))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dst = os.path.join(ROOT, "work", "analysis", "find_records.txt")
with open(dst, "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("written", dst)
