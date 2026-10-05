"""Build the "意见欲 switch unlock" mod pak.

What it does (additively only - no existing drop is modified or removed):
  * CommDropRuleDesc: append a guaranteed (weight 10000 == f10) drop of item 4096
    ("意见欲 / 大圣之意") to the drop rules used by ordinary breakable objects,
    the shrine interaction, several common world interactions and treasure boxes.
  * UnitDropRuleDesc: append a reference to the existing vanilla rule 10105
    (which already drops exactly item 4096) to every enemy drop group.

Nothing else is touched: no relic effect, no buff, no talent, no stat.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pak        # noqa: E402
import pbraw      # noqa: E402

ROOT = os.path.dirname(HERE)
GAME_PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks"

RELIC_ITEM = 4096          # 意见欲 / 大圣之意
RELIC_RULE = 10105         # vanilla rule that drops exactly item 4096

# CommDropRuleDesc rules to extend with a guaranteed relic drop
DROP_RULES = [
    91000,   # generic breakable objects (jars / boxes) - 10 destruction ids
    1008,    # shrine / rebirth point interaction (土地庙上香)
    9001,    # treasure box class 08
    2013, 2008, 2016, 2002, 2014, 2009, 3102, 5001,
]

SRC_DIR = "00Main/PBTable/"                 # path inside the game's own chunk16 pak
OUT_DIR = "b1/Content/00Main/PBTable/"      # path written into our patch pak


def relic_entry():
    """{f1: itemId, f2: count, f3: 1, f4: weight} exactly like the vanilla relic drops."""
    return pbraw.f_msg(13, b"".join([
        pbraw.enc_varint((1 << 3) | 0) + pbraw.enc_varint(RELIC_ITEM),
        pbraw.enc_varint((2 << 3) | 0) + pbraw.enc_varint(1),
        pbraw.enc_varint((3 << 3) | 0) + pbraw.enc_varint(1),
        pbraw.enc_varint((4 << 3) | 0) + pbraw.enc_varint(10000),
    ]))


def edit_drop_rules(data):
    out = bytearray()
    changed = []
    for key, start, end, rec in pbraw.iter_records(data):
        if key not in DROP_RULES:
            out += data[start:end]
            continue
        fields = pbraw.parse_fields(rec)
        # make sure the weight total exists so the weighted entry is meaningful
        if pbraw.get(fields, 10, 0) is None:
            pbraw.insert(fields, pbraw.f_uint(10, 10000))
        pbraw.insert(fields, relic_entry())
        out += pbraw.key_bytes(1, 2) + pbraw.enc_varint(len(pbraw.encode_fields(fields)))
        out += pbraw.encode_fields(fields)
        changed.append(key)
    return bytes(out), changed


def edit_unit_drops(data):
    out = bytearray()
    n = 0
    for key, start, end, rec in pbraw.iter_records(data):
        fields = pbraw.parse_fields(rec)
        pbraw.insert(fields, pbraw.f_msg(4, b"".join([
            pbraw.enc_varint((1 << 3) | 0) + pbraw.enc_varint(RELIC_RULE),
            pbraw.enc_varint((2 << 3) | 0) + pbraw.enc_varint(100000),
        ])))
        out += pbraw.key_bytes(1, 2) + pbraw.enc_varint(len(pbraw.encode_fields(fields)))
        out += pbraw.encode_fields(fields)
        n += 1
    return bytes(out), n


def main():
    game = pak.Pak(os.path.join(GAME_PAKS, "pakchunk16-Windows.pak"))
    files = {}

    # --- sanity: untouched tables must re-encode byte-identically
    for rel in ["CommDropRuleDesc.data", "UnitDropRuleDesc.data"]:
        raw = game.read(SRC_DIR + "Runtime/" + rel)
        rt = bytearray()
        for key, start, end, rec in pbraw.iter_records(raw):
            fs = pbraw.parse_fields(rec)
            rt += pbraw.key_bytes(1, 2) + pbraw.enc_varint(len(pbraw.encode_fields(fs)))
            rt += pbraw.encode_fields(fs)
        assert bytes(rt) == raw, "re-encode mismatch for " + rel
        print("  round-trip OK:", rel, len(raw), "bytes")

    raw = game.read(SRC_DIR + "Runtime/CommDropRuleDesc.data")
    new, changed = edit_drop_rules(raw)
    print("  CommDropRuleDesc: extended rules", changed)
    files[OUT_DIR + "Runtime/CommDropRuleDesc.data"] = new

    raw = game.read(SRC_DIR + "Runtime/UnitDropRuleDesc.data")
    new, n = edit_unit_drops(raw)
    print("  UnitDropRuleDesc: %d drop groups now yield the relic" % n)
    files[OUT_DIR + "Runtime/UnitDropRuleDesc.data"] = new

    out = os.path.join(ROOT, "输出", "pakchunk28-Windows_P.pak")
    pak.build_pak(files, out, mount_point="../../../", compress_zlib=True)
    print("built", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
