# AArch64 hosted target

The hosted compiler supports x86-64 (also called x64 or amd64) and an experimental
Linux AArch64 target. Both use the same hs-written frontend, IR, runtime and
backend. The target assembler and ELF writer are selected at compiler build time
through HSPATH, not when the resulting compiler runs.

Build an x86-64-hosted AArch64 compiler without running Python:

```sh
HSPATH="$PWD/selfhost/a64:$PWD/selfhost:$PWD/selfhost/be" \
  bootstrap/hs-hosted-x86_64 selfhost/be/compile.holy /tmp/hsc-a64
/tmp/hsc-a64 tests/fib.holy /tmp/fib-a64
qemu-aarch64 /tmp/fib-a64
```

On a real arm64 Linux host, the initial test build uses `a64build.py` as the
reference stage0. Its HSPATH must include `selfhost/a64` first to select the
compiler's output target as well as its host architecture. A compiler built
without that path can run on arm64 while emitting x86-64 images.

`tests/test_a64compiler.py` compares complete ELF images across `tests/*.holy`
and requires matching build/refusal classifications. Current local coverage:
70 identical images and 20 shared refusals, plus fib, dict_hash and floatlit
execution parity under QEMU. The same test runs before the broad informational
arm64 CI discovery sweep. A QEMU result is not real-hardware validation.

Limits: Linux static ELF only; dynamically linked extern libraries and x86
kernel-only instructions are refused. There is no AArch64 JIT/cache-coherency
claim. The broader runtime corpus still records two Int-width differences and
14 build refusals. The x86-64 bootstrap seed is unchanged by target selection.
