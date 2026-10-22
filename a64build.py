#!/usr/bin/env python3
"""a64build: build an arm64 ELF from a .holy program with the IR backend.

Usage: a64build.py prog.holy out   (runs under qemu-aarch64 or natively)
Reuses irx64.GenIR unchanged, with the assembler swapped for a64shim.Asm.
"""
import sys
import x64
import x64gen
import a64shim

_pack = x64.pack


def _pack_a64(code, data, start_off, lo):
    img = bytearray(_pack(code, data, start_off, lo))
    img[18:20] = (183).to_bytes(2, "little")      # EM_AARCH64
    return bytes(img)


def _no_dyn(*a, **k):
    from interp import HSErr
    raise HSErr("arm64: dynamically linked extern libraries are not supported yet", 1)


def build(prog, out):
    import irx64
    x64.pack_dyn = _no_dyn
    x64gen.Asm = a64shim.Asm
    x64.pack = _pack_a64
    return irx64.build_irx64(prog, out)


if __name__ == "__main__":
    sys.exit(build(sys.argv[1], sys.argv[2]))
