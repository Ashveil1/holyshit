# Portability: x86-64 and arm64

Status of each tier. "Verified" names the evidence.

| Piece | x86-64 | arm64 |
|---|---|---|
| Interpreter (`hs`/Python reference, tests/test.py, IR exec, LSP, docs) | CI | real arm64 hardware (ubuntu-24.04-arm discovery run): test.py 85/85, test_ir 179/179, test_irlib 107/107, test_lsp 25/25, docs 86/86 |
| A64 assembler + static ELF writer (`arm64.py`) | n/a | qemu-aarch64 in CI (`tests/test_arm64_asm.py`: fib, signed div/rem, shifts, logic, csel, write syscall) |
| IR backend (irx64/x64gen/gcrt) | CI, byte-pinned | not started (plan: x86-API shim assembler over `arm64.Asm`) |
| JIT, AOT, hosted compiler seed | CI | not supported (seed is an x86-64 ELF: "Exec format error") |
| C native backend (`native/rt.c`) | CI | fails to build: `hs_segv` reads `REG_RSP` from `ucontext` (x86 only) |
| Kernel | QEMU x86 | not planned yet |

Not verified: any hs-compiled program running on arm64, either on hardware or under emulation.

The arm64 job in `ci.yml` is informational (`continue-on-error`, dispatch/schedule only) and lists
which suites pass on real arm64. Known failures are the x86-only items in the table above.
