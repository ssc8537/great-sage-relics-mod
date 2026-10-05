"""Join ShopItemDesc/ShopItemGroupDesc/ShopDesc with ItemDesc to see what item types shops sell."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak  # noqa: E402
import pb  # noqa: E402

P = r"C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks"
p = pak.Pak(os.path.join(P, "pakchunk16-Windows.pak"))
B = "00Main/PBTable/"


def recs(rel):
    d = p.read(B + rel)
    return [f["raw"] for f in pb.parse(d) if f["no"] == 1 and f["wire"] == 2]


def flat(raw):
    r = {}
    for f in pb.parse(raw):
        r.setdefault(f["no"], []).append(
            f.get("text") if f.get("text") is not None else f.get("value", f.get("raw")))
    return r


# item types
items = {}
type_count = {}
for raw in recs("Runtime/ItemDesc.data"):
    f = flat(raw)
    iid = f[1][0]
    t = f.get(5, [None])[0]
    items[iid] = (t, (f.get(2) or [""])[0], (f.get(4) or [""])[0])
    type_count[t] = type_count.get(t, 0) + 1
print("ItemDesc item-type histogram:", sorted(type_count.items(), key=lambda kv: -kv[1])[:15])

shop_item = {}       # entry id -> (item id, ...)
for raw in recs("Runtime/ShopItemDesc.data"):
    f = flat(raw)
    shop_item[f[1][0]] = f

groups = {}
for raw in recs("Runtime/ShopItemGroupDesc.data"):
    f = flat(raw)
    groups.setdefault(f[1][0], []).append(f[2][0])
print("shop item groups:", len(groups), "sample ids:", sorted(groups)[:20])

shops = {}
for raw in recs("Runtime/ShopDesc.data"):
    f = flat(raw)
    shops[f[1][0]] = f
print("shops:")
for sid, f in shops.items():
    print("   shop", sid, {k: v for k, v in f.items() if k != 1})

# which item types are sold?
sold_types = {}
for eid, f in shop_item.items():
    iid = f.get(2, [None])[0]
    t = items.get(iid, (None,))[0]
    sold_types[t] = sold_types.get(t, 0) + 1
print("types actually sold:", sorted(sold_types.items(), key=lambda kv: -kv[1]))
print("distinct items sold:", len(shop_item))

# do any group members appear in ShopItemDesc?
sg = set()
for v in groups.values():
    sg.update(v)
print("group members also in ShopItemDesc:", len(sg & set(shop_item)), "of", len(sg))
print("sample group members:", sorted(sg)[:20])
