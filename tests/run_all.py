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
    ("test_native.py", "native (gcc)"),
    ("test_fmt.py", "formatter"),
    ("test_x64.py", "x64 backend"),
    ("test_ir.py", "IR (build/verify/exec)"),
    ("test_write_bytes_x64.py", "x64 write_bytes matches interp output and validation"),
    ("test_irx64.py", "IR->x64 differential"),
    ("test_xkernel.py", "kernel on QEMU"),
    ("test_examples.py", "examples"),
    ("test_lsp.py", "language server"),
    ("test_docs.py", "docs"),
    ("test_selfhost.py", "self-hosted lexer/parser/fmt vs Python"),
    ("test_run.py", "hs run backend selection"),
    ("test_asm.py", "assembler written in hs vs x64.py"),
    ("test_elf.py", "ELF writer written in hs vs x64.py"),
    ("test_irlib.py", "IR loader written in hs vs ir.py"),
    ("test_gcrt.py", "allocator/GC emitter written in hs vs gcrt.py"),
    ("test_iropt_hs.py", "CFG optimizer in hs vs iropt.py (interp + x64)"),
    ("test_verify_hs.py", "CFG verifier in hs vs ir.py (valid + malformed modules)"),
    ("test_irbuild.py", "AST-to-IR builder in hs vs ir.py (interp + x64)"),
    ("test_native_compiler.py", "native hs compiler image equality + full hosted fixed point"),
    ("test_be.py", "x64 backend written in hs vs irx64.py"),
    ("test_cc.py", "compiler written in hs (selfhost/cc.hs)"),
]


def main(argv):
    quick = "--quick" in argv
    failed = []
    for script, label in SUITES:
        if quick and script == "test_xkernel.py":
            print(f"skip {script:18s} ({label}) -- quick mode")
            continue
        p = subprocess.run([sys.executable, os.path.join(HERE, script)],
                           capture_output=True, text=True)
        last = [ln for ln in p.stdout.strip().split("\n") if ln][-1:]
        summary = last[0] if last else f"exit {p.returncode}"
        mark = "ok  " if p.returncode == 0 else "FAIL"
        print(f"{mark} {script:18s} ({label}): {summary}")
        if p.returncode != 0:
            failed.append(script)
            # failure lines first: the tail of a long suite can hide them
            fl = [ln for ln in p.stdout.split("\n") if ln.startswith("FAIL")]
            if fl:
                print("\n".join(x[:1500] for x in fl[:30]))
            print(p.stdout[-4000:])
            print(p.stderr[-2000:])
    if failed:
        print(f"\n{len(failed)} suite(s) failed: {', '.join(failed)}")
        return 1
    print("\nall suites passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
