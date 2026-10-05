"""Brute-force the base offset used by this game's CompressionBlocks."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak  # noqa: E402
import oodle  # noqa: E402

GAME_PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks"
p = pak.Pak(os.path.join(GAME_PAKS, "pakchunk16-Windows.pak"))
rel = "00Main/PBTable/EndingCredits/EndingCredits_EndA.data"
e = p.files[rel]
r = pak.Reader(p._read_at(e.offset, 200))
hdr = pak.read_entry(r)
data_off = e.offset + r.p
bs, be = e.blocks[0]

print("entry offset", e.offset, "hdr", r.p, "data_off", data_off, "block0", (bs, be))

for shift in range(0, 260):
    base = data_off - shift
    try:
        chunk = p._read_at(base + bs, be - bs)
    except Exception:
        continue
    try:
        out = oodle.decompress(chunk, min(e.compression_block_size, e.uncompressed))
        # verify every remaining block too
        ok = True
        tot = len(out)
        remaining = e.uncompressed - len(out)
        for (s2, e2) in e.blocks[1:]:
            n = min(e.compression_block_size, remaining)
            try:
                o = oodle.decompress(p._read_at(base + s2, e2 - s2), n)
            except Exception:
                ok = False
                break
            tot += len(o)
            remaining -= n
        print("shift=%d base=%d  block0 ok, all_ok=%s total=%d" % (shift, base, ok, tot))
        if ok:
            break
    except Exception:
        pass
