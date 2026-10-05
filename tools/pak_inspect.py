import struct, sys, os

PAK_MAGIC = 0x5A6F12E1

def read_fstring(b, off):
    n = struct.unpack_from('<i', b, off)[0]
    off += 4
    if n == 0:
        return '', off
    if n < 0:
        # utf-16
        cnt = -n
        s = b[off:off+cnt*2].decode('utf-16-le', 'replace')
        s = s.split('\x00')[0]
        return s, off + cnt*2
    s = b[off:off+n].decode('utf-8', 'replace')
    s = s.split('\x00')[0]
    return s, off + n

def main(path):
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        data = f.read()
    # search magic
    positions = []
    start = 0
    while True:
        i = data.find(struct.pack('<I', PAK_MAGIC), start)
        if i < 0: break
        positions.append(i)
        start = i + 1
    print("file size:", size)
    print("magic positions:", positions)
    if not positions:
        print("No pak magic found!")
        print("first 64 bytes:", data[:64].hex(' '))
        return
    mo = positions[-1]
    print("footer at:", mo, "bytes remaining:", size - mo)
    ver = struct.unpack_from('<i', data, mo+4)[0]
    print("version:", ver)
    off = mo + 8
    if ver >= 7:
        idx_off, idx_size = struct.unpack_from('<qq', data, off); off += 16
    else:
        idx_off, idx_size = struct.unpack_from('<ii', data, off); off += 8
    idx_hash = data[off:off+20]; off += 20
    enc = 0
    if ver >= 4:
        enc = data[off]; off += 1
    cm = 0
    if ver >= 4:
        cm = struct.unpack_from('<I', data, off)[0]; off += 4
    if ver >= 7:
        keyguid = data[off:off+16]; off += 16
        print("encryption key guid:", keyguid.hex())
    print("index offset:", idx_off, "index size:", idx_size)
    print("encrypted index:", enc, "compression methods:", hex(cm))
    # parse index
    p = idx_off
    mount, p = read_fstring(data, p)
    print("mount point:", repr(mount))
    n = struct.unpack_from('<i', data, p)[0]; p += 4
    print("num entries:", n)
    entries = []
    for i in range(n):
        name, p = read_fstring(data, p)
        eoff, esize, usize, cmeth = struct.unpack_from('<qqqI', data, p); p += 28
        # compression block sizes
        comp_blocks = []
        if cmeth != 0:
            nb = struct.unpack_from('<i', data, p)[0]; p += 4
            comp_blocks = list(struct.unpack_from('<%dI' % nb, data, p)); p += 4*nb
        # hash + flags
        if ver >= 3:
            p += 20
        encrypted = data[p]; p += 1
        cblock = 0
        if ver >= 3:
            cblock = struct.unpack_from('<I', data, p)[0]; p += 4
        entries.append(dict(name=name, off=eoff, size=esize, usize=usize, cm=cmeth,
                            blocks=comp_blocks, enc=encrypted, cblock=cblock))
    print("index consumed to:", p, "(expected", idx_off+idx_size, ")")
    print()
    print("%-100s %12s %12s %6s" % ("name", "offset", "size", "cmm"))
    for e in entries:
        print("%-100s %12d %12d %6d" % (e['name'], e['off'], e['usize'], e['cm']))
    return entries, mount, data

if __name__ == '__main__':
    main(sys.argv[1])
