"""
UE5 .pak reader/writer for Black Myth: Wukong (pak version 11, path-hash-index layout).

Format notes derived from a known-working community mod pak
(pakchunk27-Windows_P.pak):
  footer (at end of file, found by scanning back for magic 0x5A6F12E1):
      u8      encrypted_index
      u8[16]  encryption key guid
      u32     magic = 0x5A6F12E1
      u32     version = 11
      u16     UNKNOWN but constant 0x0010 in working paks  (preserved verbatim)
      u64     index_offset
      u64     index_size        (header part only, excludes phi/fdi)
      u8[20]  index sha1
      u8[32]*5  compression method names ("Zlib", ...)
  index header @index_offset:
      FString mount_point
      u32     record_count
      u64     path_hash_seed
      u32     has_path_hash_index ; u64 offset; u64 size; u8[20] hash
      u32     has_full_directory_index ; u64 offset; u64 size; u8[20] hash
      u32     encoded_entries_size ; bytes
      u32     non_encoded_entry_count (always 0 here)
  then path hash index, then full directory index at their offsets.
"""

import hashlib
import os
import struct
import zlib

MAGIC = 0x5A6F12E1
PAK_VERSION = 11
HEADER_EXTRA = 1           # extra byte after the inline entry's offset field
FOOTER_UNKNOWN = b"\x10\x00"  # 2 bytes present in working BMW paks
BMW_AES_KEY = bytes.fromhex(
    "A896068444F496956900542A215367688B49B19C2537FCD2743D8585BA1EB128")


def aes_decrypt(data, key=BMW_AES_KEY):
    from Crypto.Cipher import AES
    c = AES.new(key, AES.MODE_ECB)
    n = len(data) - (len(data) % 16)
    out = c.decrypt(data[:n]) + data[n:]
    return out
COMPRESSION_NAMES = ["Zlib", "Gzip", "Oodle", "Zstd", "LZ4"]
NUM_COMPRESSION_NAMES = 5
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x00000100000001B3


# ---------------------------------------------------------------- primitives
class Reader:
    def __init__(self, data, pos=0):
        self.d = data
        self.p = pos

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def u16(self):
        v = struct.unpack_from("<H", self.d, self.p)[0]
        self.p += 2
        return v

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.p)[0]
        self.p += 4
        return v

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def u64(self):
        v = struct.unpack_from("<Q", self.d, self.p)[0]
        self.p += 8
        return v

    def raw(self, n):
        v = self.d[self.p:self.p + n]
        self.p += n
        return v

    def fstring(self):
        n = self.i32()
        if n == 0:
            return ""
        if n < 0:
            raw = self.raw(-n * 2)
            s = raw.decode("utf-16-le", "replace")
        else:
            raw = self.raw(n)
            s = raw.decode("utf-8", "replace")
        return s.split("\x00")[0]


def _w_fstring(s):
    b = s.encode("utf-8")
    return struct.pack("<i", len(b) + 1) + b + b"\x00"


class Writer:
    def __init__(self):
        self.buf = bytearray()

    def raw(self, b):
        self.buf += b
        return self

    def u8(self, v):
        self.buf += struct.pack("<B", v)
        return self

    def u32(self, v):
        self.buf += struct.pack("<I", v)
        return self

    def u64(self, v):
        self.buf += struct.pack("<Q", v)
        return self

    def fstring(self, s):
        self.buf += _w_fstring(s)
        return self

    def pos(self):
        return len(self.buf)


# ------------------------------------------------------------------- entries
class Entry:
    __slots__ = ("offset", "compressed", "uncompressed", "compression_slot",
                 "blocks", "flags", "compression_block_size", "hash")

    def __init__(self, offset, compressed, uncompressed, compression_slot=None,
                 blocks=None, flags=0, compression_block_size=0, hash=b"\x00" * 20):
        self.offset = offset
        self.compressed = compressed
        self.uncompressed = uncompressed
        self.compression_slot = compression_slot
        self.blocks = blocks
        self.flags = flags
        self.compression_block_size = compression_block_size
        self.hash = hash

    def serialized_size(self):
        """Size of the FPakEntry structure as stored in the file data area."""
        size = 8 + HEADER_EXTRA + 8 + 8 + 4 + 20
        if self.compression_slot is not None:
            size += 4 + 16 * len(self.blocks or [])
        size += 1 + 4
        return size


def read_entry(r):
    offset = r.u64()
    r.raw(HEADER_EXTRA)
    compressed = r.u64()
    uncompressed = r.u64()
    cm = r.u32()
    slot = None if cm == 0 else cm - 1
    h = r.raw(20)
    blocks = None
    if slot is not None:
        n = r.u32()
        blocks = [(r.u64(), r.u64()) for _ in range(n)]
    flags = r.u8()
    cbs = r.u32()
    return Entry(offset, compressed, uncompressed, slot, blocks, flags, cbs, h)


def write_entry(w, e, in_data_area):
    w.u64(0 if in_data_area else e.offset)
    if in_data_area:
        w.raw(b"\x00" * HEADER_EXTRA)
    w.u64(e.compressed)
    w.u64(e.uncompressed)
    w.u32(0 if e.compression_slot is None else e.compression_slot + 1)
    w.raw(e.hash)
    if e.compression_slot is not None:
        w.u32(len(e.blocks or []))
        for start, end in (e.blocks or []):
            w.u64(start)
            w.u64(end)
    w.u8(e.flags)
    w.u32(e.compression_block_size)


def read_encoded_entry(r):
    bits = r.u32()
    slot = (bits >> 23) & 0x3F
    slot = None if slot == 0 else slot - 1
    encrypted = (bits & (1 << 22)) != 0
    block_count = (bits >> 6) & 0xFFFF
    cbs = bits & 0x3F
    if cbs == 0x3F:
        cbs = r.u32()
    else:
        cbs <<= 11

    def var_int(bit):
        return r.u32() if (bits & (1 << bit)) else r.u64()

    offset = var_int(31)
    uncompressed = var_int(30)
    compressed = uncompressed if slot is None else var_int(29)

    probe = Entry(offset, compressed, uncompressed, slot, None, 0, cbs)
    offset_base = probe.serialized_size()

    blocks = None
    if block_count == 1 and not encrypted:
        blocks = [(offset_base, offset_base + compressed)]
    elif block_count > 0:
        idx = offset_base
        blocks = []
        for _ in range(block_count):
            size = r.u32()
            blocks.append((idx, idx + size))
            idx += ((size + 15) & ~15) if encrypted else size

    return Entry(offset, compressed, uncompressed, slot, blocks,
                 1 if encrypted else 0, cbs)


def write_encoded_entry(w, e):
    cbs_field = (e.compression_block_size >> 11) & 0x3F
    if (cbs_field << 11) != e.compression_block_size:
        cbs_field = 0x3F
    block_count = len(e.blocks) if e.compression_slot is not None and e.blocks else 0

    size32 = e.compressed <= 0xFFFFFFFF
    usz32 = e.uncompressed <= 0xFFFFFFFF
    off32 = e.offset <= 0xFFFFFFFF

    flags = (cbs_field
             | (block_count << 6)
             | ((1 if e.flags & 1 else 0) << 22)
             | ((0 if e.compression_slot is None else e.compression_slot + 1) << 23)
             | ((1 if size32 else 0) << 29)
             | ((1 if usz32 else 0) << 30)
             | ((1 if off32 else 0) << 31))
    w.u32(flags)
    if cbs_field == 0x3F:
        w.u32(e.compression_block_size)
    w.u32(e.offset) if off32 else w.u64(e.offset)
    w.u32(e.uncompressed) if usz32 else w.u64(e.uncompressed)
    if e.compression_slot is not None:
        w.u32(e.compressed) if size32 else w.u64(e.compressed)
        blocks = e.blocks or []
        if len(blocks) > 1 or (e.flags & 1):
            for start, end in blocks:
                w.u32(end - start)


# ------------------------------------------------------------------ hashing
def fnv64_path(path, seed):
    h = (FNV_OFFSET + seed) & 0xFFFFFFFFFFFFFFFF
    for b in path.lower().encode("utf-16-le"):
        h ^= b
        h = (h * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h


def split_path_child(path):
    if path in ("", "/"):
        return None
    p = path[:-1] if path.endswith("/") else path
    i = p.rfind("/")
    if i < 0:
        return "/", p
    return p[:i + 1], p[i + 1:]


# -------------------------------------------------------------------- reader
class Pak:
    def __init__(self, path):
        self.path = path
        self.fh = open(path, "rb")
        self.size = os.path.getsize(path)
        self.files = {}          # rel path -> Entry
        self.mount_point = ""
        self.path_hash_seed = 0
        self.compression = []
        self._parse_footer()
        self._parse_index()

    def _read_at(self, off, n):
        self.fh.seek(off)
        return self.fh.read(n)

    def _parse_footer(self):
        tail_size = min(self.size, 600)
        tail = self._read_at(self.size - tail_size, tail_size)
        m = tail.rfind(struct.pack("<I", MAGIC))
        if m < 0:
            raise ValueError("pak magic not found")
        m += self.size - tail_size
        self.footer_magic_pos = m
        self.footer_start = m - 17
        r = Reader(self._read_at(m + 4, 46))
        self.version = r.u32()
        self.footer_unknown = r.raw(2)
        self.index_offset = r.u64()
        self.index_size = r.u64()
        self.index_hash = r.raw(20)
        self.encrypted_index = bool(self._read_at(m - 1, 1)[0])
        self.encryption_guid = self._read_at(m - 17, 16)
        names = self._read_at(m + 46, 32 * NUM_COMPRESSION_NAMES)
        self.compression = []
        for i in range(NUM_COMPRESSION_NAMES):
            name = names[i * 32:(i + 1) * 32].split(b"\x00")[0].decode("ascii", "replace")
            self.compression.append(name or None)

    def _parse_index(self):
        raw_index = self._read_at(self.index_offset, self.index_size)
        if self.encrypted_index:
            raw_index = aes_decrypt(raw_index)
        r = Reader(raw_index)
        self.mount_point = r.fstring()
        self.record_count = r.u32()
        self.path_hash_seed = r.u64()

        if r.u32() != 0:
            self.phi_offset = r.u64()
            self.phi_size = r.u64()
            r.raw(20)
        if r.u32() != 0:
            self.fdi_offset = r.u64()
            self.fdi_size = r.u64()
            r.raw(20)

        enc_size = r.u32()
        self.encoded_entries = r.raw(enc_size)
        non_encoded = r.u32()
        assert non_encoded == 0, non_encoded
        self.index_header_end = self.index_offset + r.p

        # full directory index -> path map
        fdi_raw = self._read_at(self.fdi_offset, self.fdi_size)
        if self.encrypted_index:
            fdi_raw = aes_decrypt(fdi_raw)
        fr = Reader(fdi_raw)
        dir_count = fr.u32()
        self.directories = {}
        for _ in range(dir_count):
            dirname = fr.fstring()
            files = {}
            for _ in range(fr.u32()):
                fname = fr.fstring()
                files[fname] = fr.i32()
            self.directories[dirname] = files

        for dirname, files in self.directories.items():
            for fname, eoff in files.items():
                if eoff >= 0:
                    er = Reader(self.encoded_entries, eoff)
                    e = read_encoded_entry(er)
                else:
                    raise NotImplementedError("non-encoded entry")
                rel = dirname.lstrip("/") + fname
                self.files[rel] = e

    # ---- data access
    def read(self, relpath):
        e = self.files[relpath]
        hdr_blob = self._read_at(e.offset, 4096)
        r = Reader(hdr_blob)
        hdr = read_entry(r)
        start = e.offset + r.p
        if e.flags & 1:
            # AES-256-ECB over the 16-byte-aligned payload, then trim to `compressed`
            aligned = (e.compressed + 15) & ~15
            blob = aes_decrypt(self._read_at(start, aligned))[:e.compressed]
        else:
            blob = self._read_at(start, e.compressed)
        if e.compression_slot is None:
            return blob
        name = self.compression[e.compression_slot]
        # The inlined header in the data area stores absolute (entry-relative)
        # block offsets; the index copy only carries block sizes.
        blocks = hdr.blocks or []
        multi = len(blocks) > 1
        if name == "Zlib":
            if not multi:
                return zlib.decompress(blob)
            out = bytearray()
            for (bs, be) in blocks:
                out += zlib.decompress(self._read_at(e.offset + bs, be - bs))
            return bytes(out)
        if name == "Oodle":
            import oodle
            if not multi:
                return oodle.decompress(blob, e.uncompressed)
            out = bytearray()
            remaining = e.uncompressed
            for (bs, be) in blocks:
                n = min(e.compression_block_size, remaining)
                out += oodle.decompress(self._read_at(e.offset + bs, be - bs), n)
                remaining -= n
            return bytes(out)
        raise NotImplementedError("compression " + str(name))

    def extract(self, outdir, only=None):
        for rel in self.files:
            if only and not any(pat in rel for pat in only):
                continue
            dst = os.path.join(outdir, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(self.read(rel))
            print("  extracted", rel, self.files[rel].uncompressed, "bytes")


# -------------------------------------------------------------------- writer
def build_pak(files, out_path, mount_point="../../../", compress_zlib=True,
              seed=0, footer_unknown=FOOTER_UNKNOWN, pad_entries=False):
    """files: dict rel_path -> bytes  (order is preserved in the index)"""
    w = Writer()
    entries = {}
    BLK = 0x10000
    for rel, payload in files.items():
        offset = w.pos()
        raw = payload
        slot = None
        blocks = None
        cbs = 0
        if compress_zlib and len(payload) > 64:
            nblocks = max(1, (len(payload) + BLK - 1) // BLK)
            hdr_size = 8 + HEADER_EXTRA + 8 + 8 + 4 + 20 + 4 + 16 * nblocks + 1 + 4
            parts = []
            blocks = []
            idx = hdr_size
            for i in range(0, len(payload), BLK):
                c = zlib.compress(payload[i:i + BLK], 9)
                parts.append(c)
                blocks.append((idx, idx + len(c)))
                idx += len(c)
            comp = b"".join(parts)
            if len(comp) < len(payload):
                slot = 0
                raw = comp
                # UE stores the *uncompressed* size as block size for single-block files
                cbs = len(payload) if nblocks == 1 else BLK
            else:
                blocks = None
        e = Entry(offset, len(raw), len(payload), slot, blocks, 0, cbs,
                  hashlib.sha1(payload).digest())
        write_entry(w, e, in_data_area=True)
        w.raw(raw)
        if pad_entries:
            while w.pos() % 16:
                w.u8(0)
        entries[rel] = e

    # ---- index
    encoded = Writer()
    offsets = {}
    for rel, e in entries.items():
        offsets[rel] = encoded.pos()
        write_encoded_entry(encoded, e)

    idx_start = w.pos()
    idx = Writer()
    idx.fstring(mount_point)
    idx.u32(len(entries))
    idx.u64(seed)

    phi = Writer()
    phi.u32(len(entries))
    for rel, e in entries.items():
        phi.u64(fnv64_path(rel, seed))
        phi.u32(offsets[rel])
    phi.u32(0)

    fdi_map = {}
    for rel in entries:
        p = rel
        while True:
            sc = split_path_child(p)
            if sc is None:
                break
            p = sc[0]
            fdi_map.setdefault(p, {})
        parent, name = split_path_child(rel)
        fdi_map.setdefault(parent, {})[name] = offsets[rel]

    fdi = Writer()
    fdi.u32(len(fdi_map))
    for dirname, fl in fdi_map.items():
        fdi.fstring(dirname)
        fdi.u32(len(fl))
        for fname, off in fl.items():
            fdi.fstring(fname)
            fdi.u32(off)

    header_size = (4 + len(mount_point.encode()) + 1 + 4 + 8
                   + 4 + 8 + 8 + 20 + 4 + 8 + 8 + 20
                   + 4 + len(encoded.buf) + 4)
    phi_offset = idx_start + header_size
    fdi_offset = phi_offset + len(phi.buf)

    idx.u32(1)
    idx.u64(phi_offset)
    idx.u64(len(phi.buf))
    idx.raw(hashlib.sha1(bytes(phi.buf)).digest())
    idx.u32(1)
    idx.u64(fdi_offset)
    idx.u64(len(fdi.buf))
    idx.raw(hashlib.sha1(bytes(fdi.buf)).digest())
    idx.u32(len(encoded.buf))
    idx.raw(bytes(encoded.buf))
    idx.u32(0)

    assert idx.pos() == header_size, (idx.pos(), header_size)

    w.raw(bytes(idx.buf))
    w.raw(bytes(phi.buf))
    w.raw(bytes(fdi.buf))

    # ---- footer (BMW order: guid, encrypted_index, magic, version, ...)
    w.raw(b"\x00" * 16)          # encryption key guid
    w.u8(0)                      # encrypted index
    w.u32(MAGIC)
    w.u32(PAK_VERSION)
    w.raw(footer_unknown)
    w.u64(idx_start)
    w.u64(header_size)
    w.raw(hashlib.sha1(bytes(idx.buf)).digest())
    for i in range(NUM_COMPRESSION_NAMES):
        name = COMPRESSION_NAMES[i].encode() if i < len(COMPRESSION_NAMES) else b""
        slot = bytearray(32)
        slot[:len(name)] = name
        w.raw(bytes(slot))

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(bytes(w.buf))
    return out_path


if __name__ == "__main__":
    import sys
    if sys.argv[1] == "list":
        p = Pak(sys.argv[2])
        print("mount:", p.mount_point, "seed:", p.path_hash_seed)
        for k, v in sorted(p.files.items()):
            print("  %-80s off=%-10d comp=%-9d raw=%-9d slot=%s blocks=%s" %
                  (k, v.offset, v.compressed, v.uncompressed, v.compression_slot,
                   len(v.blocks) if v.blocks else 0))
    elif sys.argv[1] == "extract":
        p = Pak(sys.argv[2])
        p.extract(sys.argv[3])
