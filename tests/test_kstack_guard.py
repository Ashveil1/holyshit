#!/usr/bin/env python3
"""main-frame vs ring-3 entry zone guard: python3 tests/test_kstack_guard.py

Pins the structural invariant behind the info_bytes stray-fault fix: the
ring-3 exception/IRQ entry zone (CPU frame + 15-register stub save = up to
168 bytes) is written at RSP0 = stack_top, so hs_kernel_main's frame must
start strictly below it. build_xkernel reserves kstack_ KMAIN_GUARD bytes
larger and starts main at stack_top - KMAIN_GUARD. This test checks the
built image itself: the movabs that loads rsp and the TSS RSP0 field must
differ by exactly KMAIN_GUARD. No QEMU needed.
"""
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import x64gen
from x64gen import build_xkernel

os.environ["HSPATH"] = ROOT + os.pathsep + os.environ.get("HSPATH", "")

fails = 0
total = 0


def check(name, cond, detail=""):
    global fails, total
    total += 1
    if cond:
        print(f"ok   {name}")
    else:
        print(f"FAIL {name} {detail}")
        fails += 1


GUARD = x64gen.KMAIN_GUARD
# entry zone: 48-byte CPU frame (ring change + error code) + 120-byte stub
# register save; the guard must cover it with room for nested entries.
check("KMAIN_GUARD covers the 168-byte entry zone", GUARD >= 4096,
      f"KMAIN_GUARD={GUARD}")

d = tempfile.mkdtemp(prefix="kguard_")
img_path = os.path.join(d, "kernel")
rc = build_xkernel(os.path.join(ROOT, "kernel", "xdemo.holy"), img_path)
check("xdemo kernel build", rc == 0, f"rc={rc}")
img = open(img_path, "rb").read()

# main's entry rsp: the patched movabs rsp, imm64 in the kernel VA range
main_rsps = []
i = img.find(b"\x48\xbc")
while i != -1:
    imm = struct.unpack("<Q", img[i + 2:i + 10])[0]
    if x64gen.KBASE < imm < 0x2000000:  # kernel image VAs, below KHEAP_BASE
        main_rsps.append(imm)
    i = img.find(b"\x48\xbc", i + 1)
check("exactly one kernel-range movabs rsp", len(main_rsps) == 1,
      f"found {len(main_rsps)}: {[hex(v) for v in main_rsps]}")

if main_rsps:
    main_rsp = main_rsps[0]
    rsp0 = main_rsp + GUARD
    # the TSS starts [0:4]=0, [4:8]=RSP0 low 32 bits, [8:64]=0 (the I/O
    # bitmap offset at 66:68 is set, so don't match past 64)
    tss_pat = b"\0" * 4 + struct.pack("<I", rsp0 & 0xFFFFFFFF) + b"\0" * 56
    check("TSS RSP0 == main entry rsp + KMAIN_GUARD",
          img.count(tss_pat) == 1,
          f"main_rsp={hex(main_rsp)} expected RSP0={hex(rsp0)}, "
          f"TSS pattern found {img.count(tss_pat)}x")

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
