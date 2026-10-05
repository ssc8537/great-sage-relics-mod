"""Minimal generic protobuf wire-format decoder / encoder (no .proto needed)."""

import struct
import sys


def read_varint(buf, pos):
    result = 0
    shift = 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def write_varint(v):
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def try_decode_string(b):
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not s:
        return ""
    printable = sum(1 for c in s if c.isprintable() or c in "\r\n\t")
    if printable / len(s) > 0.9:
        return s
    return None


def parse(buf, start=0, end=None, depth=0, maxdepth=6):
    """Yield dicts describing fields: {no, wire, value, raw, start, end}"""
    if end is None:
        end = len(buf)
    pos = start
    fields = []
    while pos < end:
        fstart = pos
        try:
            key, pos = read_varint(buf, pos)
        except IndexError:
            break
        fno, wire = key >> 3, key & 7
        f = {"no": fno, "wire": wire, "start": fstart}
        if wire == 0:
            f["value"], pos = read_varint(buf, pos)
        elif wire == 2:
            ln, pos = read_varint(buf, pos)
            data = buf[pos:pos + ln]
            if len(data) != ln:
                raise ValueError("truncated")
            f["raw"] = data
            pos += ln
            sub = None
            if depth < maxdepth and ln > 0:
                try:
                    sub = parse(buf, f["raw"] and 0, ln, depth + 1, maxdepth) if False else None
                except Exception:
                    sub = None
                try:
                    subfields = _parse_bytes(data, depth + 1, maxdepth)
                    if subfields is not None:
                        sub = subfields
                except Exception:
                    sub = None
            f["sub"] = sub
            f["text"] = try_decode_string(data)
        elif wire == 5:
            f["value"] = struct.unpack_from("<I", buf, pos)[0]
            pos += 4
        elif wire == 1:
            f["value"] = struct.unpack_from("<Q", buf, pos)[0]
            pos += 8
        else:
            raise ValueError("bad wire type %d at %d" % (wire, fstart))
        f["end"] = pos
        fields.append(f)
    return fields


def _parse_bytes(data, depth, maxdepth):
    """Return subfields only if data parses cleanly as a message."""
    try:
        sub = parse(data, 0, len(data), depth, maxdepth)
    except Exception:
        return None
    if not sub:
        return None
    consumed = sub[-1]["end"]
    if consumed != len(data):
        return None
    return sub


def dump(buf, depth=0, out=sys.stdout, prefix=""):
    fields = parse(buf, 0, len(buf), depth)
    for f in fields:
        pad = "  " * depth
        if f["wire"] == 0:
            print("%s#%d varint %d" % (pad, f["no"], f["value"]), file=out)
        elif f["wire"] == 2:
            t = f["text"]
            if f["sub"]:
                print("%s#%d msg(%d bytes)" % (pad, f["no"], len(f["raw"])), file=out)
                dump(f["raw"], depth + 1, out)
            elif t is not None:
                print("%s#%d str %r" % (pad, f["no"], t), file=out)
            else:
                print("%s#%d bytes %s" % (pad, f["no"], f["raw"][:32].hex()), file=out)
        else:
            print("%s#%d wire%d %d" % (pad, f["no"], f["wire"], f["value"]), file=out)


if __name__ == "__main__":
    data = open(sys.argv[1], "rb").read()
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10 ** 9
    import io
    s = io.StringIO()
    dump(data, 0, s)
    txt = s.getvalue().splitlines()
    print("\n".join(txt[:limit]))
    print("... total lines:", len(txt))
