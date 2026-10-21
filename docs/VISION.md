# holyshit - VISION

> Written 2026-10-12 at **v0.6.30**, from goals stated by the project owner (Ash) himself.
> Current evidence checkpoint updated 2026-10-21; original goals retained (see `docs/bench.md`).
> This file is "the goals you can look up any time" - the hands-on plan lives in [`ROADMAP.md`](ROADMAP.md)
>
> Labels in this file: **[documented]** = written down in SPEC/docs/commits ·
> **[measured]** = has numbers or tests in the repo · **[inferred]** = this
> document author's own summary, no confirming file · **[missing]** = not found in the repo

## The 7 goals (owner's words, summarized)

holyshit (hs) will be a language that:

1. **Is faster than Python**
2. **Needs no explicit compile step - runs JIT-style** (write and run immediately, but native-fast)
3. **Is easier to write than Python**
4. **Can build an OS by itself** with almost no other language
5. **Is fully self-reliant** (self-reliant: no gcc/as/ld/libc needed; eventually the compiler is written in hs itself)
6. **Interoperates with other languages** - can call other languages' libraries (FFI)
7. **Is designed for AI as the primary author** - aims to be the language AI writes best

**Dropped from the goals (owner's call 2026-10-12):** full Python-library
compatibility - not required (FFI goal 6 stays, but no CPython C-API / numpy support)

## Status per goal (at v0.6.30)

### Current evidence checkpoint: 2026-10-21

This checkpoint replaces the original v0.6.30 status assessment. The seven
owner goals above are unchanged. Passing tests establish the stated scope,
not completion of a whole goal.

| Goal | What is demonstrated | What remains |
|---|---|---|
| Faster than Python | `bench/run.py` checks equal outputs against CPython. Local int/recursion cases are about 5-6x faster; alloc/dict/string results vary. Hash-indexed dicts and conservative mark-sweep GC replaced the original bottlenecks. Since 2026-10-19 the JIT driver gained a persistent compiled-code cache (warm startup 30 ms -> 7 ms on the JSON bench) and inline fast paths for generic `==`/`!=` and `len()`. | Larger workloads, lower live-heap overhead, repeatable results on other machines. No universal speed claim. |
| No explicit compile / JIT | Default `hs run` builds and runs x64 with caching/fallback. `scripts/run-native.sh` compiles and runs through the native hs seed without Python/gcc. An experimental eager in-memory JIT driver (`selfhost/be/jit_run.holy`, see `docs/jit.md`) compiles source to machine code and executes it in-process with a persistent code cache. | The JIT driver is eager, not first-call or tiered. Type feedback, inline caching and deoptimization are not implemented. |
| Easier than Python | Methods on builtins, lambda, classes/inheritance, f-strings, comprehensions, default arguments, prelude helpers, formatter, errors, REPL and LSP exist. | No human usability or model comparison establishes that hs is easier. Syntax is not Python-compatible. |
| Write an OS in hs | Public xkernel uses IR. Full CI runs the unchanged QEMU corpus, 291/291, on IR and retained AST paths. The hs IR kernel compiler produces reference-identical complete ELFs. `scripts/build-kernel-native.sh` builds without Python/gcc/as/ld. | Real hardware, network stack, disk filesystem, SMP/USB/graphics and a standalone boot/distribution story are not established by these gates. |
| Self-reliance | Parser, normalization, IR builder/optimizer/verifier, x64 runtime/code generator, assembler and ELF linker have hs implementations. An audited Linux x86-64 seed compiles itself twice with seed == stage2 == stage3. The hosted/native kernel routes need no Python execution. The JIT emitter itself is written in hs (no LLVM/external libraries), per the owner's 2026-10-18 directive. | The repository still uses Python for reference semantics, tests, regeneration, tooling and an independent source audit. The seed needs repository sources/runtime data; it is not a portable standalone distribution. |
| Interoperation | C ABI I64/U64/F64/Str/Ptr/U0 works in interp, native and x64. A struct-by-pointer regression uses gmtime_r and explicit field access. Bare soname externs (such as "m") resolve through the FFI library search path. | Struct-by-value, callbacks and variadic calls are not supported. No broad language-library compatibility claim. |
| AI-first | Structured errors, formatter, test runner, explanations, LSP, API docs and 39 evaluation tasks/checker exist. | No model run or pass@1 result. A task count is not an AI-quality measurement. |

Overall progress is approximately **70%**, an engineering estimate against
these seven goals, not a percentage calculated from tests or a promise that
80% is reached. The largest unfinished areas are real JIT (first-call
compilation, tiering, type feedback), wider FFI, GC/performance work and
measured AI/usability evaluations.

Evidence and commands: [`ROADMAP.md`](ROADMAP.md), [`bench.md`](bench.md),
[`jit.md`](jit.md), [`../bootstrap/README.md`](../bootstrap/README.md),
`tests/test_native_compiler.py`, `tests/test_hosted_seed.py`,
`tests/test_native_kernel_ir.py`, `tests/test_native_kernel_command.py`,
`tests/test_xkernel.py` and `tests/test_kernel_ir.py`.

## Tensions inside the goals (decisions needed - see ROADMAP "Risks")

- **JIT + no compile step vs full self-reliance:** a JIT needs a machine-code
  generator running in the same process (possible, since the `x64.py` encoder
  exists) - but writing it in Python would still depend on Python, so the
  owner directed (2026-10-18) that the JIT emitter be written in hs itself,
  x86-64, with no LLVM or external libraries
- **Faster than Python vs detailed error messages + tagged values:** SPEC §13 measured that error checks cost speed
- **Easier than Python (dynamic) vs fast (static):** a fully dynamic language means the JIT needs type feedback/specialization
- **Use everything like every language vs dropping Python libraries:** the owner dropped the latter; FFI is the answer instead
