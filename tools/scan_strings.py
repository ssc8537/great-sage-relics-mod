"""Scan every PBTable .data in the game for given UTF-8 strings."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak  # noqa: E402

GAME_PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks"
NEEDLES = [s.encode("utf-8") for s in (sys.argv[1:] or ["意见欲", "合意同心", "根器"])]

p = pak.Pak(os.path.join(GAME_PAKS, "pakchunk16-Windows.pak"))
rels = [k for k in p.files if "PBTable" in k]
print("scanning", len(rels), "files for", NEEDLES)
hits = 0
for rel in sorted(rels):
    data = p.read(rel)
    found = [n.decode("utf-8") for n in NEEDLES if n in data]
    if found:
        hits += 1
        print("HIT", rel, found)
print("total files with hits:", hits)
