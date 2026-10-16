# Exact-key scalar native function experiment

```sh
export HSPATH="$PWD/selfhost:$PWD/selfhost/be"
export HSROOT="$PWD"
bootstrap/hs-hosted-x86_64 selfhost/be/jit_function_probe.holy /tmp/hs-function
/tmp/hs-function tests/fib.holy 'fib$L1' '[[10], [15]]'
```

This diagnostic initializes one isolated target module once, then invokes one
exact local IR function key repeatedly while keeping its runtime/heap alive.
Each argument set has exact declared arity;1..32 sets are accepted. Arguments
must be signed30-bit integers. The generated per-set no-argument C ABI shim
pushes tagged immediate integers and an empty closure environment, calls the
existing native function label, saves a tagged integer result and returns a
separate status. Non-integer results are rejected without reading or exporting
target objects. Captures, module entry keys and missing/nonlocal keys reject.

The key is compiler-internal (for example `fib$L1`), not a stable public export
name. It bypasses current dynamic name lookup and any later rebinding of the
module's function variable. This direct code-identity diagnostic must not be
used as normal source-language name dispatch. Arity defaults are not applied.
It is not a documented application function ABI or a safe plugin interface.

The module keeps globals/imports/heap across calls. Each invocation installs a
root native handler, sets the GC stack boundary to its current shim frame and
saves/restores C ABI callee-saved registers/stack. Captured language errors
copy bytes/line into driver memory; later calls can continue. Finally and inner
handlers run as usual. Target mutations before an error persist, not rollback.
After the last controlled call, target-owned GC mappings and image are released.
If module initialization errors, calls are skipped and teardown still runs.

`JIT FUNCTION INITIAL` reports module status. `JIT FUNCTION RESULTS` reports
one status/integer-or-copied-error pair per call. Those markers are diagnostic,
not target output; captured errors do not become process exit status. Rejected
non-integer returns and driver/compile/fatal failures stop the process and do
not claim normal teardown. No automatic retry or in-place reload is added.

The independent test compares recursive, zero/six-argument, stateful, finally/
error-then-success and allocation-heavy repeated calls with ordinary reference
calls, including a rooted global list surviving target GC. Existing isolated
sequence/status/return/ownership gates remain. The30-bit argument restriction
keeps transport bounded; it is not the language's whole integer range.

There are still no shared language objects/closures/GC roots or exceptions
between the driver and target, no foreign callbacks, cold execution tier,
hotness counters/dispatch cells, invalidation or deoptimization. Fatal exits,
OOM/handler overflow, signals and unsafe corruption remain outside recovery;
externs reject, files/arbitrary process side effects are not cleaned up.
This is a bounded function-return experiment for stage2, not tiering or a
performance claim.
