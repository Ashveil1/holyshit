# Hosted compiler seed

The source of the hosted compiler is `selfhost/be/compile.hs` and its hs
imports. The Python implementation stays as the semantic/test reference.

The Linux x86-64 seed `hs-hosted-x86_64` is pinned by `SHA256SUMS`.
It was accepted after the native compiler passed full CI and its source
bootstrap/fixed-point gates. `scripts/verify-hosted-seed.py` compares it to
a compiler built from this source before executing it, then checks another
generation. That audit uses Python as the independent reference.

For Python-free bootstrap, run `scripts/bootstrap-seed.sh [output-dir]`.
It checks the pinned hash before executing the seed, builds stages two and
three and requires both to match the seed byte for byte. The seed is Linux
x86-64 only, 9,273,760 bytes. It uses the repository source and runtime data;
it is not a standalone distribution. To rebuild without trusting the seed,
use `scripts/bootstrap-hosted.sh` (Python stage zero, native later stages).

SHA256: `262e9247a4d35c1eb7383a4fb51a99b3be85e17aed0b090a60e9f171aecb5519`.
Changing compiler sources may change the fixed point. Regenerate and verify
the seed rather than silently accepting an old binary or updating the hash.

The hosted compiler is not the kernel compiler. Its full-width unsafe
literal gate now covers decimal and hex words through 64 bits. Safe tagged
integer behavior is unchanged. Kernel compilation is a separate artifact.

## Run source without Python

`scripts/run-native.sh path/to/program.hs [args...]` verifies the pinned
seed, compiles to an isolated temporary executable, runs it, returns the
program's exit code and removes the temporary directory. No explicit build
step, Python or gcc is needed. This is native compile-and-run, not a
method JIT or interpreter fallback. Imports use the source directory and
`HSPATH`; execution keeps the caller's working directory. The compiler
still supports only its documented hosted subset and reports unsupported
programs rather than falling back to Python. No persistent cache is used.

## Build a kernel without Python

`scripts/build-kernel-native.sh source.hs kernel.elf` verifies the pinned
hosted seed, uses it to build the native hs IR kernel driver, then writes
the kernel ELF through the hs IR backend and linker. It needs only shell
utilities at runtime, not Python, gcc, as or ld. It does not boot the kernel
or package a ramdisk. Source and output paths may contain spaces. An
existing output is preserved when parsing or compilation fails.
