"""Dump printable ASCII / UTF-16 strings from a binary file (for UE asset spelunking)."""
import re
import sys


def strings(path, minlen=4):
    data = open(path, "rb").read()
    out = []
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, data):
        out.append(("ascii", m.start(), m.group().decode("ascii")))
    for m in re.finditer((rb"(?:[\x20-\x7e]\x00){%d,}" % minlen), data):
        out.append(("utf16", m.start(), m.group().decode("utf-16le")))
    out.sort(key=lambda t: t[1])
    return out


if __name__ == "__main__":
    for path in sys.argv[1:]:
        dst = path.replace("/", "_").replace("\\", "_") + ".strings.txt"
        lines = ["%08x %-5s %s" % (off, kind, s) for kind, off, s in strings(path)]
        with open(dst, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("wrote", dst, len(lines), "strings")
