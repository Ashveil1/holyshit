#!/usr/bin/env python3
"""Run every holyshit suite: python3 tests/run_all.py [--quick]

--quick skips test_xkernel.py (needs qemu-system-x86_64 and boots 24 kernels).

Suites:
  test.py         51  interpreter (reference semantics)
  test_native.py  52  gcc native backend, byte-identical to interp
  test_fmt.py      4  formatter canonical + idempotent + same behavior
  test_x64.py    102  x86-64 backend, static ELF, no gcc
  test_ir.py     141  IR: build/verify/exec byte-identical to interp
  test_irx64.py   44  IR->x64 ELF agrees with AST-path ELF
  test_xkernel.py 291 freestanding kernel booting on QEMU
  test_examples.py 17  every examples/*.hs still runs (interp + native)
  test_lsp.py     25  language server over stdio
  test_docs.py    41  doc examples really run, links + api.json stay in sync
  test_selfhost.py 808 self-hosted lexer/parser/formatter (hs) match the Python ones on every repo .hs
  test_run.py     45  `hs run` backend choice, fallback, overrides
  test_asm.py      1  selfhost/asm.hs (assembler in hs) == x64.py byte for byte (17.8k instrs)
  test_elf.py      1  selfhost/elf.hs (ELF writer in hs) == x64.py pack() byte for byte
  test_irlib.py    1  selfhost/irlib.hs (IR loader in hs) == ir.parse_module on every lowerable repo program
  test_gcrt.py     1  selfhost/gcrt.hs (allocator/GC emitter in hs) == gcrt.py byte for byte
  test_be.py      58  selfhost/be (irx64 + x64gen runtime translated to hs) == irx64.py images
  test_cc.py      79  selfhost/cc.hs (compiler written in hs) emits ELFs equal to interp
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SUITES = [
    ("test.py", "interpreter"),
    ("test_native_strings.py", "UTF-8 literals and embedded-NUL display/key bytes"),
    ("test_native.py", "native (gcc)"),
    ("test_fmt_controls.py", "formatter preserves every ASCII control byte"),
    ("test_fmt.py", "formatter"),
    ("test_x64.py", "x64 backend"),

    ("test_holy_bridge.py", "reference/GCC/LSP .holy compatibility stage"),
