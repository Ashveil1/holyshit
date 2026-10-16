# Tiered JIT workstream

Long-term direction: a real cold execution tier with selective compilation of
hot code, followed by guarded specialization. Experimental eager compilation
in `docs/jit.md` is useful prior work, but is not this system. Nothing here
relabels eager whole-program compilation as tiering. No performance or date
promise is made.

## Stages and acceptance boundaries

1. Reference instrumentation, now available only through the Python IR API.
   `ExecutionProfile` in `irprofile.py` counts function and block entries and
   up to eight argument-type vectors without retaining argument values.
   Collection is opt-in, saturating and site-bounded. It does not select code
   or run native code. This is a correctness/debugging scaffold, not the final
   self-hosted cold tier. It supports only the existing reference IR subset.
2. Resumable native runtime ABI. Current generated `_start` exits its process;
   define function entry/return, boxed-value ownership, exception status,
   closure environment and GC roots before any mixed-tier execution. Verify
   interpreted -> native -> interpreted calls and errors. No magic jump into
   existing process-entry code.
3. Self-hosted cold execution tier and counters. Match `interp.py` on the
   supported corpus including recursion, classes, closures, finally/unwind,
   mutable aliasing, GC and FFI boundaries. Keep the existing eager route.
4. Baseline hot-function compilation with a stable dispatch cell and whole
   function safe-entry boundaries. Avoid on-stack replacement initially.
   Compiled code must share the cold runtime's objects, roots and exceptions.
   Bound counters/cache space and verify threshold+eviction correctness.
5. Guards and deoptimization. Define a recovery map for every exit before
   specializing. Reconstruct frames, temporaries and exception/finally state;
   mutations/print/FFI cannot be repeated. Test forced failures at every guard.
6. Measured optimization. Separate cold startup, first compilation, warm
   throughput, memory and compile time; compare reference, baseline, optimized
   and AOT with equal inputs and checked output. Existing `bench/run.py` and
   `bench/jit.py` remain prior baselines, not tiered performance evidence.

Each stage may need several focused PRs with exact-head full CI. The x86 OS
lane continues separately. ARM64 is later. Agent-centered OS design does not
imply a model, desktop, networking or privilege isolation already exists.

## Diagnostic API

```python
from irprofile import ExecutionProfile
profile = ExecutionProfile(max_sites=1024)
ir.run_module(module, basedir, profile=profile)
snapshot = profile.snapshot()
```

`version: 1` snapshots identify `reference-ir-profile-not-jit`. Site identity
is the builder's qualified function name plus entry/block label, local to
that module build. Do not combine profiles from different sources as a cache.
Block visits include loop visits and exception handler entries; they are not
an exact loop-backedge counter. Snapshots own their lists, so later edits do
not mutate collection. Collector scope clears/restores on every exit. The
reference IR executor already has global state and is not thread-safe; this
API adds no concurrency promise. No automatic CLI output or profile files.

## Return-boundary experiment

The [one-shot return probe](jit-return-probe.md) now exercises a normally
returning native module entry without replacing `_start`. It is deliberately
not a shared-runtime ABI: errors can exit, heaps are process-owned and no
objects cross runtimes. Stage2 is still incomplete.

## Isolated error-outcome experiment

The [status probe](jit-status-probe.md) adds a root native handler and returns
language-error metadata instead of exiting for errors that reach it. It copies
error bytes before destroying the target heap/image and can print them after
teardown. This is still one independent runtime, no shared object or exception
identity, and no resumable function ABI. Fatal exits/signals remain outside
capture. Stage2 remains incomplete; this does not add any execution tier.

The [sequence experiment](jit-sequence-probe.md) now repeats fresh isolated
module creation/teardown in one driver, including error then success. It does
not reuse one module's functions or share its values/roots. This verifies a
finite lifecycle boundary only; stage2 remains incomplete.

The [exact-key scalar function probe](jit-function-probe.md) keeps one target
runtime alive across repeated native calls and captured errors. It transports
only immediate integers, bypasses dynamic name lookup, and has no shared
language values/roots or cold-tier caller. This is a bounded stage2 experiment,
not a stable public function ABI or hot-function tier.
