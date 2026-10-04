#!/usr/bin/env python3
"""Pack a directory into a KRFS ramdisk image for holyshit kernels.

    python3 scripts/mkramdisk.py kernel/ramdisk /tmp/ramdisk.krfs

KRFS v1 layout (all little-endian, every field padded to 4 bytes so the
kernel only needs load32, which is alignment-safe on every backend):
    "KRFS" | u32 nentries
    per entry: u32 type (0 = file, 1 = dir) | u32 path_len | path bytes +
               pad-to-4 | u32 size | data bytes + pad-to-4
Paths are slash-separated, relative, without leading slash. Entries are
sorted (dirs before the files they contain) so a single pass creates them.
"""
import os
import struct
import sys


def pad4(b):
    return b + b"\0" * (-len(b) % 4)


def main():
    src, out = sys.argv[1], sys.argv[2]
    entries = []  # (path, is_dir, bytes)
    for root, dirs, files in os.walk(src):
        dirs.sort()
        for d in sorted(dirs):
            p = os.path.relpath(os.path.join(root, d), src)
            entries.append((p.replace(os.sep, "/"), True, b""))
        for f in sorted(files):
            full = os.path.join(root, f)
            p = os.path.relpath(full, src)
            with open(full, "rb") as fh:
                entries.append((p.replace(os.sep, "/"), False, fh.read()))
    entries.sort(key=lambda e: (e[0].count("/"), e[0]))
    buf = bytearray()
    buf += b"KRFS"
    buf += struct.pack("<I", len(entries))
    for path, is_dir, data in entries:
        pb = path.encode("utf-8")
        buf += struct.pack("<I", 1 if is_dir else 0)
        buf += struct.pack("<I", len(pb))
        buf += pad4(pb)
        buf += struct.pack("<I", len(data))
        buf += pad4(data)
    with open(out, "wb") as fh:
        fh.write(bytes(buf))
    print(f"wrote {out} ({len(buf)} bytes, {len(entries)} entries)")


main()
