"""Verify the built mod pak: structure, and that only the intended fields changed."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pak      # noqa: E402
import pbraw    # noqa: E402

ROOT = os.path.dirname(HERE)
GAME_PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks"
MOD = os.path.join(ROOT, "输出", "pakchunk28-Windows_P.pak")
SRC_DIR = "00Main/PBTable/Runtime/"
OUT_DIR = "b1/Content/00Main/PBTable/Runtime/"

game = pak.Pak(os.path.join(GAME_PAKS, "pakchunk16-Windows.pak"))
mod = pak.Pak(MOD)
print("mod pak: mount=%r files=%d" % (mod.mount_point, len(mod.files)))
for k, e in sorted(mod.files.items()):
    print("   %-58s raw=%-7d comp=%-7d slot=%s blocks=%s"
          % (k, e.uncompressed, e.compressed, e.compression_slot,
             len(e.blocks) if e.blocks else 0))


def rec_map(data):
    return {key: rec for key, _s, _e, rec in pbraw.iter_records(data)}


for name in ["CommDropRuleDesc.data", "UnitDropRuleDesc.data"]:
    a = game.read(SRC_DIR + name)
    b = mod.read(OUT_DIR + name)
    ma, mb = rec_map(a), rec_map(b)
    assert set(ma) == set(mb), "record keys changed in " + name
    changed = []
    bad = []
    for k in ma:
        if ma[k] == mb[k]:
            continue
        la = [(f["no"], f["raw"]) for f in pbraw.parse_fields(ma[k])]
        lb = [(f["no"], f["raw"]) for f in pbraw.parse_fields(mb[k])]
        # every original field must still be present, in order, untouched
        it = iter(lb)
        kept = all(any(x == f for x in it) for f in la)
        added = [x for x in lb if x not in la]
        changed.append((k, len(la), len(lb), added))
        if not kept:
            bad.append(k)
    print("\n== %s: %d/%d records changed" % (name, len(changed), len(ma)))
    for k, na, nb, added in changed[:4]:
        kinds = sorted({n for n, _r in added})
        print("   key %-8s fields %d -> %d  (appended field numbers %s)" % (k, na, nb, kinds))
    if len(changed) > 4:
        print("   ... and %d more" % (len(changed) - 4))
    print("   PROBLEM - originals not preserved as an ordered subsequence:", bad or "none")

# show the edited relic entry once
b = mod.read(OUT_DIR + "CommDropRuleDesc.data")
for key, _s, _e, rec in pbraw.iter_records(b):
    if key == 91000:
        print("\n== rule 91000 after edit:")
        for f in pbraw.parse_fields(rec):
            print("   f%-3d w%d %s" % (f["no"], f["wire"], f["raw"].hex()))
        break
