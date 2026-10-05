"""Raw-preserving protobuf field editor.

Re-encoding an untouched message with these helpers is byte-identical to the
input, so tables can be edited additively without disturbing the game's own
serialization choices.
"""
import struct


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


def enc_varint(v):
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def key_bytes(no, wire):
    return enc_varint((no << 3) | wire)


def parse_fields(buf):
    """-> list of dicts {no, wire, raw, payload}; raw is the complete field bytes."""
    out = []
    pos = 0
    n = len(buf)
    while pos < n:
        start = pos
        key, pos = read_varint(buf, pos)
        no, wire = key >> 3, key & 7
        if wire == 0:
            _, pos = read_varint(buf, pos)
            payload = None
        elif wire == 2:
            ln, pos = read_varint(buf, pos)
            payload = buf[pos:pos + ln]
            pos += ln
        elif wire == 5:
            pos += 4
            payload = buf[pos - 4:pos]
        elif wire == 1:
            pos += 8
            payload = buf[pos - 8:pos]
        else:
            raise ValueError("bad wire type %d at %d" % (wire, start))
        out.append({"no": no, "wire": wire, "raw": buf[start:pos], "payload": payload})
    return out


def f_uint(no, value):
    return {"no": no, "wire": 0, "raw": key_bytes(no, 0) + enc_varint(value), "payload": None}


def f_msg(no, payload):
    return {"no": no, "wire": 2,
            "raw": key_bytes(no, 2) + enc_varint(len(payload)) + payload,
            "payload": payload}


def encode_fields(fields):
    return b"".join(f["raw"] for f in fields)


def insert(fields, new_field):
    """Insert keeping the ascending field-number order the game uses."""
    pos = len(fields)
    for i, f in enumerate(fields):
        if f["no"] > new_field["no"]:
            pos = i
            break
    fields.insert(pos, new_field)
    return fields


def get(fields, no, wire=None):
    for f in fields:
        if f["no"] == no and (wire is None or f["wire"] == wire):
            return f
    return None


def set_uint(fields, no, value):
    f = get(fields, no, 0)
    if f is None:
        insert(fields, f_uint(no, value))
    else:
        f["raw"] = key_bytes(no, 0) + enc_varint(value)
    return fields


def iter_records(table_bytes, record_field=1):
    """Yield (key, start, end, raw) for top-level repeated message records."""
    pos = 0
    n = len(table_bytes)
    while pos < n:
        start = pos
        key, p = read_varint(table_bytes, pos)
        no, wire = key >> 3, key & 7
        if wire != 2:
            # not a record-shaped table
            raise ValueError("unexpected wire type %d in table" % wire)
        ln, p = read_varint(table_bytes, p)
        rec = table_bytes[p:p + ln]
        end = p + ln
        sub = parse_fields(rec)
        rkey = sub[0]["payload"] if sub and sub[0]["wire"] == 0 else None
        rkey = None
        if sub and sub[0]["wire"] == 0:
            rkey, _ = read_varint(rec, len(key_bytes(sub[0]["no"], 0)))
        if no == record_field:
            yield rkey, start, end, rec
        pos = end
