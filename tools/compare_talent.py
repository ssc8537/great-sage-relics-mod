"""Compare the case mod's TalentSDesc.data against the vanilla base table."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pb  # noqa: E402

ROOT = os.path.dirname(HERE)
MOD = os.path.join(ROOT, "work", "sample_extract", "b1", "Content", "00Main", "PBTable",
                   "Runtime", "TalentSDesc.data")
VAN = os.path.join(ROOT, "work", "vanilla", "base", "00Main", "PBTable", "Runtime",
                   "TalentSDesc.data")


def records(path):
    data = open(path, "rb").read()
    out = {}
    for f in pb.parse(data):
        if f["no"] == 1 and f["wire"] == 2:
            fields = pb.parse(f["raw"])
            tid = None
            for g in fields:
                if g["no"] == 1 and g["wire"] == 0:
                    tid = g["value"]
            out[tid] = f["raw"]
    return out


def flat(raw):
    """flatten one record into {field_no: [values]} with str/bytes/varint decoded"""
    res = {}
    for f in pb.parse(raw):
        if f["wire"] == 0:
            res.setdefault(f["no"], []).append(("v", f["value"]))
        elif f["wire"] == 2:
            res.setdefault(f["no"], []).append(("s", f["text"] if f["text"] is not None
                                                else f["raw"].hex()))
        else:
            res.setdefault(f["no"], []).append(("w%d" % f["wire"], f["value"]))
    return res


m = records(MOD)
v = records(VAN)
print("mod records", len(m), "vanilla records", len(v))
only_mod = sorted(set(m) - set(v))
only_van = sorted(set(v) - set(m))
print("only in mod:", only_mod[:50])
print("only in vanilla:", only_van[:50])

diffs = 0
for tid in sorted(set(m) & set(v), key=lambda x: (x is None, x)):
    a, b = flat(m[tid]), flat(v[tid])
    if a == b:
        continue
    diffs += 1
    if diffs <= 40:
        print("---- ID", tid)
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                print("   f%-3d mod=%s" % (k, a.get(k)))
                print("        van=%s" % (b.get(k),))
print("total differing records:", diffs)
