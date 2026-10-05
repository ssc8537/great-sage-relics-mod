"""Debug multi-block compressed entries in the game paks."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak  # noqa: E402

GAME_PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks"
p = pak.Pak(os.path.join(GAME_PAKS, "pakchunk16-Windows.pak"))
rels = [k for k in p.files if "PBTable" in k]
for rel in sorted(rels):
    e = p.files[rel]
    if e.compression_slot is None or not e.blocks or len(e.blocks) <= 1:
        continue
    hdr_blob = p._read_at(e.offset, 200)
    r = pak.Reader(hdr_blob)
    hdr = pak.read_entry(r)
    print("REL", rel)
    print("  offset=%d header_size=%d r.p(after read_entry)=%d serialized_size()=%d"
          % (e.offset, r.p, r.p, hdr.serialized_size()))
    print("  compressed=%d uncompressed=%d cbs=%d slot=%s nblocks=%d"
          % (e.compressed, e.uncompressed, e.compression_block_size,
             p.compression[e.compression_slot], len(e.blocks)))
    print("  blocks:", e.blocks)
    print("  header hex:", hdr_blob[:80].hex())
    break
