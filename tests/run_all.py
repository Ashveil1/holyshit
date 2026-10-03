#!/usr/bin/env python3
"""Run every holyshit suite: python3 tests/run_all.py [--quick]

--quick skips test_xkernel.py (needs qemu-system-x86_64 and boots 58 kernels).

Suites:
  test.py         35  interpreter (reference semantics)
  test_native.py  36  gcc native backend, byte-identical to interp
  test_fmt.py      4  formatter canonical + idempotent + same behavior
  test_x64.py     25  x86-64 backend, static ELF, no gcc
  test_xkernel.py 62  freestanding kernel booting on QEMU
  test_examples.py 17  every examples/*.hs still runs (interp + native)
  test_lsp.py     25  language server over stdio
  test_docs.py    33  doc examples really run, links + api.json stay in sync
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
    ("test_xkernel.py", "kernel on QEMU"),
    ("test_examples.py", "examples"),
    ("test_lsp.py", "language server"),
    ("test_docs.py", "docs"),
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
            print(p.stdout[-4000:])
            print(p.stderr[-2000:])
    if failed:
        print(f"\n{len(failed)} suite(s) failed: {', '.join(failed)}")
        return 1
    print("\nall suites passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
