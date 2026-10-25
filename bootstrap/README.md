# Hosted compiler seed

The source of the hosted compiler is `selfhost/be/compile.holy` and its hs
imports. The Python implementation stays as the semantic/test reference.

The Linux x86-64 seed `hs-hosted-x86_64` is pinned by `SHA256SUMS`.
It was accepted after the native compiler passed full CI and its source
bootstrap/fixed-point gates. `scripts/verify-hosted-seed.py` compares it to
a compiler built from this source before executing it, then checks another
generation. That audit uses Python as the independent reference.

For Python-free bootstrap, run `scripts/bootstrap-seed.sh [output-dir]`.
It checks the pinned hash before executing the seed, builds stages two and
three and requires both to match the seed byte for byte. The seed is Linux
x86-64 only, 10,181,328 bytes. It uses the repository source and runtime data;
it is not a standalone distribution. To rebuild without trusting the seed,
use `scripts/bootstrap-hosted.sh` (Python stage zero, native later stages).

SHA256: `2e7680ddb9aeaa4b43ce34fb17091f32b4d265e6e33cadef6b52eba8dbe18df7`.
Changing compiler sources may change the fixed point. Regenerate and verify
the seed rather than silently accepting an old binary or updating the hash.

The hosted compiler is not the kernel compiler. Its full-width unsafe
literal gate now covers decimal and hex words through 64 bits. Safe tagged
integer behavior is unchanged. Kernel compilation is a separate artifact.

## Run source without Python

`scripts/run-native.sh path/to/program.holy [args...]` verifies the pinned
seed, compiles to an isolated temporary executable, runs it, returns the
program's exit code and removes the temporary directory. No explicit build
step, Python or gcc is needed. This is native compile-and-run, not a
method JIT or interpreter fallback. Imports use the source directory and
`HSPATH`; execution keeps the caller's working directory. The compiler
still supports only its documented hosted subset and reports unsupported
programs rather than falling back to Python. No persistent cache is used.

## Build a kernel without Python

`scripts/build-kernel-native.sh source.holy kernel.elf` verifies the pinned
hosted seed, uses it to build the native hs IR kernel driver, then writes
the kernel ELF through the hs IR backend and linker. It needs only shell
utilities at runtime, not Python, gcc, as or ld. It does not boot the kernel
or package a ramdisk. Source and output paths may contain spaces. An
existing output is preserved when parsing or compilation fails.

## Build a relocatable native directory

```
scripts/build-native-bundle.sh /tmp/hs-native
/tmp/hs-native/bin/hs run path/to/program.holy [args...]
/tmp/hs-native/bin/hs build path/to/program.holy output
```

The output directory must not already exist. The builder verifies the seed
and builds the eager driver once, then includes the compiler, hs sources,
standard modules and runtime JSON code. Move the whole directory together.
The launcher resolves data relative to itself; the original checkout is not
needed at runtime. Source imports still resolve from the source directory.
No Python or gcc is needed to build or run the bundle. Linux x86-64, `/bin/sh`
and standard shell/checksum utilities are required. Eager FFI uses host libc
and shared libraries. This is not a static binary or a cross-platform bundle.

`run` compiles eagerly in memory, not on first function call. It has no tiering,
cache or interpreter fallback. Unlike scripts/run-jit-native.sh, it does not
rebuild the driver on every launch. Checksums catch accidental binary changes,
not a maliciously replaced binary and checksum file together. `build` retains
the compiler's current failure and output behavior.
