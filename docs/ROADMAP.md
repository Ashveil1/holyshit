# holyshit - ROADMAP

> Written 2026-10-12 from **v0.6.30**, aiming at the goals in [`VISION.md`](VISION.md)
> Second revision after reading code/running tests/measuring benchmarks for real: numbers in [`bench.md`](bench.md)
> Labels: **[documented]** = written down in the repo · **[inferred]** = the planner's hypothesis, must be confirmed with the owner/code ·
> Ordering and durations are proposals, not promises (no pre-v0.6.30 roadmap exists in the repo beyond the IR plan)
>
> Principle: every phase needs a **runnable pass gate** (command + expected result), existing tests stay green
> (`python3 tests/run_all.py`), and every change is followed by a benchmark

## Current status: 2026-10-21

The seven-goal evidence table is maintained in [VISION.md](VISION.md).
Overall progress is about **70%**, an engineering judgment, not a test-derived
score. **80% has not been reached.** Old phase durations below are historical
planning estimates, not current delivery commitments.

Completed native B-path checkpoints:

- Hosted hs compiler includes normalized parsing, optimized/verified IR,
  module loading, x64 runtime, GC emission, static/dynamic ELF and C ABI.
  `tests/test_native_compiler.py` requires complete image equality against
  the Python reference and a two-generation native fixed point. Unsafe
  literal transport covers decimal/hex words through 64 bits; safe tagged
  integer semantics remain unchanged.
- `bootstrap/hs-hosted-x86_64` is a pinned Linux x86-64 seed, rebuilt and
  re-pinned whenever the compiler closure changes (current hash in
  `bootstrap/SHA256SUMS`). The source audit rebuilds it independently; the
  Python-free bootstrap requires seed == stage2 == stage3. It depends on
  this repository, not Python execution. See [bootstrap instructions](../bootstrap/README.md).
- `scripts/run-native.sh SOURCE [args...]` is one-command compile-and-run.
  It is not JIT and does not silently fall back to Python.
- Public xkernel selects IR. The unchanged QEMU corpus passes 291/291
  through IR and retained AST lowerings. The native hs IR kernel compiler
  matches complete reference ELF images, and
  `scripts/build-kernel-native.sh SOURCE OUTPUT` packages this Python-free
  path. This does not claim hardware validation or a standalone OS.
- Immutable-string allocation was compacted. Nine alternating local runs
  reduced string-benchmark median runtime 0.580149s -> 0.520208s and peak
  RSS 469 MB -> 377 MB. See [benchmark scope](bench.md). A GC arena-cache
  experiment was rejected after it did not improve alternating medians.
- Experimental eager in-memory JIT driver (`selfhost/be/jit_run.holy`):
  compiles source to machine code, relocates it into owned RX mappings and
  executes in-process (see [jit.md](jit.md)). Since 2026-10-19 it has a
  persistent compiled-code cache (json bench warm startup 30 ms -> 7 ms),
  an FFI soname fix, and inline fast paths for generic `==`/`!=` and
  `len()` in the hs emitter. All of this is written in hs itself -
  no LLVM or external code-generation libraries (owner directive 2026-10-18).

Immediate unfinished work:

1. Real in-memory JIT beyond the eager driver: first-call compilation,
   tiering, type feedback/specialization, deopt, with
   execution/relocation/lifetime/error gates before claiming it replaces
   compile-and-run.
2. Broader FFI (callbacks, struct-by-value, variadics) and explicit ABI tests.
3. GC/live-heap performance and more representative benchmarks.
4. Actual model evaluations on the 39-task suite and usability comparisons.

`selfhost/cc.holy` and the M1-M5 subset bootstrap are historical groundwork,
not the current full hosted compiler. The current entrypoint is
`selfhost/be/compile.holy`. Python remains the semantic/reference and
regeneration toolchain, not a required runtime for the native B-path.
Each implementation stage still needs its own PR, differential regression
and green full CI before normal merge.

## What was measured before starting (v0.6.30, see `bench.md`)

- interp/x64/IR/irx64/fmt/LSP/docs tests all pass; native and kernel (QEMU) cannot run on the measuring machine -> CI confirms
- xbuild is 5-6x faster than CPython on int/function-call work
- dict 200k insert: 117 s (CPython 0.1 s) due to linear scan; alloc 5M loop: 687 MB because nothing frees
- The language still lacks class/method/lambda and non-Str dict keys

## Phase 0 - trustworthy foundations (done)

| Work | Status |
|---|---|
| CI (`.github/workflows/ci.yml`): quick on every push/PR; nightly = full suite + QEMU + bench | done |
| `bench/` .holy/.py pairs + `bench/run.py` + `docs/bench.md` baseline | done |
| Sync version/test counts in README/AGENTS/run_all | done |
| tag `v0.6.30` | done at the baseline commit |
| LICENSE | done (Apache License 2.0, copyright 2026 Ashveil1) |

## Phase 1 - speed/memory dead spots (in progress)  [goals 1, 5]

1. **Hash dict on x64 (done):** a dict with >= 8 keys builds a hash table (FNV-1a, open addressing, load <= 0.5) beside the original key/value pair array
   (insertion order preserved; small dicts stay linear scan) - 200k insert: 117 s -> 0.05 s (CPython 0.08 s); test `tests/dict_hash.holy` compares against interp
2. **Memory reclamation:** a free list alone does not help because nobody knows what is dead, so a GC is needed -
   plan: conservative mark-sweep, running only at "safe points" the IR backend emits (function entries/loop back-edges) so runtime helpers
   are never interrupted mid-call; 16-byte header per block + block-start bitmap per arena; `unsafe` blocks allocated by `x_alloc` are pinned and not collected
   Pass gate: `bench/alloc` uses < 50 MB, all suites green, stress tests (nested list/dict/closure/exception) match interp;
   if it cannot be made stable, revert and keep it as phase 3 work (new runtime in hs)

## Phase 2 - move the kernel to IR and close the old AST backend (1-2 weeks)  [goals 4, 5]

Rationale [documented]: SPEC §15.35/15.38: `xkernel` still used `x64gen.build_x64_ast`; `xbuild` already used IR (v0.6.28)

1. Add freestanding lowering (serial, heap, IDT, PIT, port I/O, `unsafe`) in `irx64.py`
2. Run the kernel corpus (`kernel/*.holy`, 291 cases) through the IR path, ELF-to-ELF + QEMU against the AST path
3. Switch `hs.py xkernel` to IR; keep the AST path behind a flag for one release, then delete
4. Give the IR path the same full corpus walk v0.6.30 gave `xbuild` (to find bugs like the 5 found then)

**Done:** `test_xkernel.py` passes 291/291 on the IR path in full CI; `xkernel` defaults to IR (see "S8 default kernel IR" below).

## Phase 3 - language capability + optimizer (4-6 weeks)  [goals 1, 3, 7]

The language still lacks things AI/people expect from Python: methods on builtins (`s.split(",")`, `l.append(x)`, `d.get(k)`), lambda, non-Str dict keys, class/struct with methods, string formatting.
Every feature must: be specified in SPEC first, change `interp.py` first (the behavior prototype), then IR/x64/native follow with differential tests.

[documented] Today: tagged values (Int 62-bit), non-freeing bump allocator on x64, Boehm GC on native.

- 3.1 If the phase 1 GC does not pass: allocator + GC written in hs/IR (new runtime) - needed for long programs, kernel, JIT and self-hosting
- 3.2 IR optimizations: constant folding, dead code, small-function inlining, mem2reg (the IR plan says deferred)
  [documented: "variables do not get mem2reg since..."] - every one must preserve "byte-exact match with interp"
- 3.3 Simple register allocation (linear scan) instead of using the stack for everything **[inferred - check what x64gen does today]**
- 3.4 Fix the recorded divergence: Int 62-bit on x64 vs 64-bit on interp - pick one (bigint/overflow semantics)
- **Pass gate:** phase 1 benches improve to target with no regression in interp-equality tests; a program allocating 10^8 times does not run out of memory

## Phase 4 - JIT (historical duration estimate; implementation remains open)  [goals 2, 1]

Existing base [documented]: IR (`ir.py`) + x64 backend (`irx64.py`) + encoder (`x64.py`) without libc.
Owner directive (2026-10-18): the JIT emitter is written in holyshit itself, x86-64, no LLVM/external libraries.

Current state (2026-10-21): an experimental eager in-memory driver exists
(`selfhost/be/jit_run.holy`, `scripts/run-jit-native.sh`) with a persistent
code cache. It compiles the whole program eagerly, relocates into owned RX
mappings and executes in-process. There is no first-call compilation,
tiering, type feedback or deoptimization yet.

Design (proposal **[inferred]**):
1. **"Compile-on-first-call" JIT next** (method JIT without tiering): on `hs prog.holy` -> parse -> IR -> machine code into mmap(RW->RX) -> jump in
2. Keep the interpreter as the lower tier (reference behavior + fallback for out-of-subset features)
3. **Sub-phase 4b:** type feedback + specialization (Int/Float/Str fast paths, guard + deopt back to interp)
   because the language is fully dynamic; start with inline caching of `+ - < ==` and indexing
4. Cache compiled code (a .hsc file beside the source) to cut startup - still "no explicit compile from the user's view" (done for the JIT driver)
5. `hs prog.holy` stays a single command with no user-visible `build`; `build`/`xbuild` remain for AOT/binary delivery

**Pass gate:** `hs prog.holy` starts running in <50 ms for small programs (measured), stdout/stderr/rc byte-identical to interp
on the same corpus as phase 2, bench >= `xbuild` ± 10% and better than CPython per phase 1 targets

## Phase 5 - Self-hosting (historical plan; native gates now implemented)  [goal 5]

Rationale: originally parser/IR/backend/LSP were Python; SPEC §15.35 called IR "the first step of the self-hosting plan"

Order **[inferred]**:
1. **Make the language sufficient to write a compiler:** real dict/hash, string builder, full file I/O, good errors, deep recursion/stack,
   memory management (phase 3.1) - build a "what is missing to write a lexer" list by actually writing one
2. Write the **lexer + parser in hs** (AST must match `interp.parse_program`, dump-compared across the corpus)
3. Write the **IR builder + verifier in hs** (compared with `ir.py` via the IR text dump `hs.py ir`)
4. Write the **x64 backend + assembler/ELF writer in hs** (`x64.py`, `x64gen.py`, `irx64.py` ~ 600 KB - mostly `x64gen.py`,
   which should be replaced by `irx64`; cut the old one before porting)
5. **bootstrap:** stage0 = current Python -> compile stage1 (hs compiler as ELF) -> stage1 compiles itself = stage2;
   **pass gate:** stage1 and stage2 are byte-identical binaries (fixed point) and pass the whole suite
6. Remove Python/gcc/Boehm from the main path (`build` via gcc stays an option)

**Status 2026-10-21:** steps 1-5 are done for the hosted compiler (pinned seed,
seed == stage2 == stage3 fixed point, `scripts/run-native.sh`). Step 6 is done
for the hosted/native-kernel routes; Python remains the reference/test toolchain.

## Phase 6 - practical FFI (2-4 weeks, can run parallel to phases 3-5)  [goal 6]

[documented] Today: `extern` through the C ABI, basic types, no struct/callback/variadic, forbidden in unsafe/kernel.

1. Check `extern` on `xbuild` (SPEC §15.22-15.28 said missing at v0.6.14-15) and bring it level with native
2. Data types: struct by pointer/by value, arrays, callbacks (hs function -> C function pointer), variadics (`printf`)
3. A self-written `.so` loader on x64 without libc if feasible (own dynamic ELF loader/`dlopen`) **[inferred - big job; alternative: static linking through our own linker]**
4. Automatic binding generator from C header files (`hs.py bind foo.h`)
5. Examples and tests with Rust / Zig / C++ exporting the C ABI (as SPEC §11 claims) - test for real on a machine with those compilers
- **Pass gate:** call libc (`printf`, `qsort` with callback), libm, at least one external C library (e.g. sqlite or zlib) and a Rust-built `.so` from hs in interp, build and xbuild modes
- Out of scope (dropped): CPython C-API / full Python libraries

## Phase 7 - a complete-enough OS (ongoing)  [goal 4]

What exists [documented]: up to an ATA PIO driver (v0.6.17) plus, since then, VFS/file I/O and floats in the native IR kernel compiler gate. Not in the read SPEC and needs checking [inferred]: network, real disk/filesystem on disk, SMP, ACPI/APIC, graphics, own bootloader, running on real hardware

Proposed order: (1) filesystem on disk (ext2-like or simpler) over ATA (2) ELF loader in the kernel running user
programs written in hs (3) own bootloader/UEFI or multiboot without QEMU `-kernel` (4) network (virtio-net or e1000 + small ARP/IP/UDP/TCP)
(5) APIC/new timer/SMP (6) boot on real hardware/other VMs
**Pass gate per item:** automated QEMU tests (extending `test_xkernel.py`) + a short demo

## Phase 8 - AI-first: measure and strengthen (alongside every phase from phase 1)  [goals 7, 3]

Base [documented]: AGENTS.md, for-agents.md, api.json, errors.md, `--json` errors, LSP, test-checked docs

1. **eval suite:** 50-100 programming tasks (`evals/*.md` + automatic tests); run with several models in "with docs" and "without docs" modes; metrics: pass@1, fix iterations, tokens per program; compare Python on the same tasks
2. Every error gets a code + fix hint (`E0xx: ...; hint: ...`) as JSON (extending errors.md)
3. Canonical `hs fmt` that does not strip comments (done: `fmt -w` keeps comments (positions may shift, blank lines still drop)) - AI can write comments without losing them
4. "agent mode" commands: `hs check --json`, `hs explain <error>`, `hs test` with JSON output; an LSP usable through MCP/CLI
5. Remove language ambiguity (one way to write things), remove memorized divergences (e.g. `/` in unsafe vs safe)
6. A runnable "task -> code" example set for models to learn from in context
- **Pass gate:** eval results reported every release; target **[inferred]** pass@1 >= 80% of Python on the same task set when given AGENTS.md as context

## Order summary

```
phase 0 (CI/base) -> phase 1 (bench+eval start) -> phase 2 (kernel->IR)
      -> phase 3 (language+optimizer) -> phase 4 (JIT) -> phase 5 (self-host)
      parallel: phase 6 (FFI), phase 7 (OS), phase 8 (AI eval) throughout
```

## Risks and blunt observations

1. **Huge scope for one person/AI help** (language + 4 backends + JIT + OS + self-host + FFI) - finish phases 0-2 first
   and define which workloads "faster than Python" is measured on, starting in phase 1
2. **JIT on a fully dynamic language is hard** - without type feedback it only reaches "baseline" speed; acceptable if the target is beating CPython, not matching V8/LuaJIT
3. **"Fully self-reliant" conflicts with "interoperates with every language":** FFI through the C ABI needs a dynamic loader - without libc it must be written from scratch
4. **Byte-exact equality with interp** is this project's strength (differential testing) but means semantic changes (e.g. Int 64-bit) must change interp first
5. **Old tests could not see bugs** (v0.6.30 found 5) -> add fuzz/differential testing as a staple of every phase, not just hand-written cases
6. **A new language + AI-first:** models have never seen hs in training data; quality depends entirely on docs/examples/errors, so measure (phase 8), do not guess
7. **Limits of this planner's understanding:** read SPEC, README, docs/index.md, commit log and the IR plan headings but did not run tests or benchmarks;
   all time numbers come from the SPEC and were not re-measured

## Assumptions to confirm

- Speed targets (how many times CPython, on which workloads) - the owner has not given numbers
- Preferred license (currently Apache License 2.0)
- Whether the OS should run on real hardware or QEMU only
- Whether Python may remain the permanent stage0 of the bootstrap (first time only) or not
- Priority order among phase 4 (JIT), phase 5 (self-host) and phase 7 (OS)
  (owner answered 2026-10-18: self-reliance wins - the JIT emitter is written in hs itself)

## B-path compiler port checkpoints (2026-10-14)

- S1: `asm.holy` + `elf.holy` emit the same static ELF bytes as Python.
- S2: `irlib.holy` reads the existing textual IR interchange.
- S3: `gcrt.holy` and `be/be.holy` emit byte-identical hosted images on the
  single-file differential corpus. Module source lowering, dynamic ELF/FFI,
  and a full compiler fixed point are not yet proved.
- S5a: `be/irbuild.holy` lowers the canonical parser AST to the unoptimized
  flat CFG used by `ir.py`. `_n`/`_t` records, block/temp numbering, functions,
  unsafe operations, closures and finally inlining must match structurally.
  `test_irbuild.py` feeds the same canonical AST JSON to Python and hs,
  validates each result with the Python verifier, and compares the whole
  module. The hs builder is tested through interp and a compiled x64 driver;
  ASTs containing integers outside the x64 62-bit payload are explicitly
  interp-only. Parser normalization (defaults/range/prelude), the optimizer,
  the self-hosted verifier, module loading and bootstrap are separate gates.
  This checkpoint does not claim a Python-free compiler.

S5b optimizer checkpoint: `be/iropt.holy` folds and removes unused constants
with whole-module structural equality to `iropt.py`, through interp and x64.
A separate seeded boundary matrix checks arithmetic folding near the 62-bit
limits. Multiplication is bounded before it can wrap into a false constant.
This stage still consumes canonical IR JSON; parser normalization and the
full compiler driver are not part of this checkpoint.
S5 verifier checkpoint: `be/verify.holy` checks CFG labels, terminators,
SSA definitions, dominance, phi predecessors and instruction uses. Valid
corpus modules and deliberately malformed modules are checked against the
Python verifier, through interp and x64. Out-of-width IR constants remain
interp-only. This is a compiler-stage check, not a full bootstrap claim.
Compiler-depth regression gate: repeated returns from an except handler
must pop the active exception value, not the already-consumed try frame.
`tests/t_exceptreturn.holy` exercises 300 handled returns with and without
finally. The Python IR builder and its hs translation share this cleanup
rule; interp remains the output oracle.

Native hosted-compiler checkpoint: `selfhost/be/compile_hex.holy` builds through
Python stage0, then the resulting native compiler builds itself. The test
requires stage1 == stage2 == stage3 byte for byte. Output is chunked hex to
bound memory; this driver is not a polished CLI. `test_native_compiler.py`
also compares hosted ELF output against Python across the source corpus.
One full-width unsafe-constant program remains explicitly deferred. A
successful hosted fixed point does not cover the separate kernel backend,
all 64-bit unsafe values, or the missing x64 write_bytes helper. No binary
seed is yet committed. The Python source remains the reference/test oracle.

The x64 IR path now supports direct `write_bytes(path, [Int 0..255])`.
Validation runs before opening the file; empty data and embedded zero bytes
are preserved. `test_write_bytes_x64.py` compares exact file bytes and
catchable failures with interp, including invalid elements and non-list
inputs. First-class write_bytes values remain outside the x64 subset.

Source-to-ELF driver checkpoint: `selfhost/be/compile.holy SOURCE OUTPUT`
connects normalized parsing, optimized IR, verification, module loading,
JSON helper compilation and static/dynamic ELF emission. Its interp-run
image must equal the Python backend byte for byte, including module and
FFI programs. This is not yet a Python-free bootstrap: compiling this
compiler to x64 and reaching a fixed point remain separate gates.

S5c parser normalization: `be/normalize.holy` applies default-argument filling,
range-step lowering and prelude injection after `parselib.parse`. Prelude
source is copied from the reference as data by `scripts/mkprelude.py`.
`test_normalize.py` compares the full normalized AST; `test_pipeline.py`
compares source -> optimized CFG through interp and compiled x64. The
13k-line backend emitter is explicitly deferred to a separate slow bootstrap
gate, and out-of-width ASTs are interp-only. Modules are lowered individually
here; linking their imports belongs to the compiler-driver stage.
Compiler-depth regression gate: repeated returns from an except handler
must pop the active exception value, not the already-consumed try frame.
`tests/t_exceptreturn.holy` exercises 300 handled returns with and without
finally. The Python IR builder and its hs translation share this cleanup
rule; interp remains the output oracle.
S5 verifier checkpoint: `be/verify.holy` checks CFG labels, terminators,
SSA definitions, dominance, phi predecessors and instruction uses. Valid
corpus modules and deliberately malformed modules are checked against the
Python verifier, through interp and x64. Out-of-width IR constants remain
interp-only. This is a compiler-stage check, not a full bootstrap claim.

The x64 IR path now supports direct `write_bytes(path, [Int 0..255])`.
Validation runs before opening the file; empty data and embedded zero bytes
are preserved. `test_write_bytes_x64.py` compares exact file bytes and
catchable failures with interp, including invalid elements and non-list
inputs. First-class write_bytes values remain outside the x64 subset.

### S8 experimental kernel IR lowering
The IR kernel lowering passed the existing QEMU behavioral corpus
291/291 in full CI alongside the retained AST lowering. The default-switch
checkpoint below moves the public xkernel command to IR. IR emits different code, so whole-image
byte equality is not the right comparison between those two lowerings.
The gate is the unchanged kernel corpus's serial output and machine-state
checks, repeated through `tests/test_kernel_ir.py`. Hosted behavior must
remain unchanged. Kernel runtime, IRQ/task/syscall helpers and ELF boot
layout reuse the established implementation. The full QEMU gate passed before the default-switch checkpoint.
Measured binary-driver fixed point: scripts/bootstrap-hosted.sh produced
three identical 9,080,008-byte ELF compilers locally. Stages two and three
were built by the native compiler with no Python process in those steps.
The seed is not committed and full CI remains the merge gate.

### S6 native unsafe words
The native compiler parses unsafe integer literals through 64 bits as eight
little-endian bytes when they exceed its tagged integer range. This is a
compiler-internal AST/IR transport only, not a change to language integers.
Decimal and hex words, including unary minus, must produce the same ELF as
the reference compiler. Larger unsafe literals fail rather than truncate.
The t_load64 exclusion is removed; boundary cases and the two-generation
compiler fixed point remain required tests. This does not claim kernel
self-hosting or change safe integer overflow behavior.
### S7a boot assembler
`selfhost/asm32.holy` supplies the 32-bit instruction/fixup layer used by the
multiboot-to-long-mode stub. `tests/test_asm32.py` checks all instruction
forms, register pairs, immediate boundaries and symbolic fixes byte for
byte against `x64.Asm32`, through both interp and compiled x64. This is a
kernel-bootstrap component only, not a native kernel compiler claim.

### S7b multiboot linker
`selfhost/klink.holy` lays out ELF32 headers, multiboot headers, boot32 code,
GDT/TSS, long-mode payload, IRQ gates, page tables and stack patches. Its
inputs are the payload assembler state and stack-patch offset. The test
captures real AST-backend payloads before the Python linker mutates them,
then requires byte-identical complete ELF images from the hs linker on
interp and compiled x64. It covers heap, ring3, syscall, preemption, JSON
and user-shell kernels. This proves linking only: source-to-kernel native
compilation and the kernel IR migration remain separate gates.

### S7c native kernel compiler prototype
`selfhost/be/kernel_hex.holy` uses the maintained AST kernel backend and hs
multiboot linker. Seven complete kernel ELF images match the reference:
basic runtime, heap, ring3, syscall, preemption, JSON and user shell.
Port fixes cover Scope identity, module parsing, global names, assembler
defaults, wide kernel literals and UTF-8 data emission. Backend regeneration
must remain exact. The UTF-8 helper initially exhausted memory during self-build. Avoiding
per-ASCII-character JSON allocation restores the hosted fixed-point gate
(24/24 targeted gates, including two generations). Full CI is pending;
kernel IR migration and Python-free seed packaging are still separate work.


### Timer IRQ register preservation
The no-scheduler timer path must preserve interrupted general-purpose
registers. Its PIC acknowledgement now saves and restores RDX around
port I/O before returning or capturing a scheduled context. A deterministic
software interrupt exercises the real timer IDT vector without relying on
PIT timing. Hosted behavior is unchanged; native kernel images and the
hosted compiler seed remain source-equality gates.

### S8 default kernel IR
After the same QEMU corpus passed 291/291 on both lowerings in full CI,
public `xkernel` selects IR by default. The AST lowering is retained as
`build_xkernel(..., ir_backend=False)` and the behavioral corpus runs on
both in full CI. Native kernel compiler image gates still compare with
AST explicitly: the native kernel driver has not migrated to IR yet.
This default switch does not claim native IR kernel self-hosting.

### S8 native IR kernel compiler
`selfhost/be/kernel_ir_hex.holy` lowers source through the hs IR builder,
verifier, IR machine-code backend and multiboot linker. Complete kernel
ELF images must match the Python IR backend byte for byte. The gate covers
heap, ring3, syscalls, preemption, JSON, shell, VFS/file I/O, ATA, floats
and address spaces. AST image equality remains a separate reference gate.
Kernel adapter methods preserve tagged versus raw words, builtin precedence
and runtime allocation of literal strings/floats. Hosted compiler
self-compilation and source-audited pinned seed gates still apply.

### S9 Python-free kernel command
`scripts/build-kernel-native.sh source.holy kernel.elf` builds the hs IR kernel
driver with the audited seed and runs it. Integration gates compare complete
ELFs with the Python IR oracle under a PATH without Python/gcc and verify
that a compile failure leaves an existing output unchanged. This packages
the native path; it is not a kernel boot command or a standalone OS image.

### Reading the earlier implementation checkpoints
Earlier checkpoints above describe the state when that stage was developed.
Statements such as "seed not committed", "full CI pending", "native kernel
driver has not migrated to IR" and "one unsafe constant deferred" are
superseded by the current status at the top and the later S6-S9 gates. They
are retained as development history, not current blockers.
