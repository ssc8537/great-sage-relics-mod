"""Reconstruct the shop structure: groups, their items (with names), refresh and shop rows."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak  # noqa: E402
import pb  # noqa: E402

P = r"C:\Program Files (x86)\Steam\steamapps\common\BlackMythWukong\b1\Content\Paks"
p = pak.Pak(os.path.join(P, "pakchunk16-Windows.pak"))


def recs(rel):
    d = p.read("00Main/PBTable/" + rel)
    return [f["raw"] for f in pb.parse(d) if f["no"] == 1 and f["wire"] == 2]


def flat(raw):
    r = {}
    for f in pb.parse(raw):
        r.setdefault(f["no"], []).append(
            f.get("text") if f.get("text") is not None else f.get("value", f.get("raw")))
    return r


items = {}
for raw in recs("Runtime/ItemDesc.data"):
    f = flat(raw)
    items[f[1][0]] = (f.get(2, [""])[0], f.get(4, [""])[0], f.get(5, [None])[0])

groups = {}
for raw in recs("Runtime/ShopItemGroupDesc.data"):
    f = flat(raw)
    groups.setdefault(f[1][0], []).append((f[2][0], f.get(3, [None])[0]))

import io
_buf = io.StringIO()


def out(*a):
    print(*a, file=_buf)


out("=== groups (%d)" % len(groups))
for gid in sorted(groups):
    mem = groups[gid]
    names = ["%s(%s)" % (i, (items.get(i) or ("?", "", None))[1] or (items.get(i) or ("?",))[0])
             for i, _ in mem]
    out("group %-6s n=%-3d %s" % (gid, len(mem), ", ".join(names[:8])))

out("")
out("=== ShopItemDesc sample (entry -> item, name, price-ish fields)")
si = recs("Runtime/ShopItemDesc.data")
for raw in si[:20]:
    f = flat(raw)
    iid = f.get(2, [None])[0]
    out("  entry %-8s item %-8s %-10s fields=%s" % (
        f[1][0], iid, (items.get(iid, ("?",))[1] or "?"),
        {k: v for k, v in f.items() if k != 1}))

out("")
out("=== ShopRefreshDesc (all 52)")
for raw in recs("Runtime/ShopRefreshDesc.data"):
    f = flat(raw)
    out("  ", {k: v for k, v in f.items()})

_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "work", "analysis", "shop_structure.txt")
with open(_path, "w", encoding="utf-8") as fh:
    fh.write(_buf.getvalue())
print("wrote", _path)
