# Target-native global/closure dispatch experiment

```sh
export HSPATH="$PWD/selfhost:$PWD/selfhost/be"
export HSROOT="$PWD"
bootstrap/hs-hosted-x86_64 selfhost/be/jit_dispatch_probe.holy /tmp/hs-dispatch
/tmp/hs-dispatch tests/fib.holy fib '[[10], [15]]'
```

This diagnostic initializes one isolated target module once, then invokes a
named main-module global through ordinary generated native call lowering.
Unlike the [exact-code-key experiment](jit-function-probe.md), it reloads the
global value each time. A function that rebinds that global changes later
calls; aliases and closures keep the existing target Func/capture semantics.
No target closure or object is exported into the driver's separate heap.

Preparation inserts one private uncalled IR wrapper that calls the selected
global with its parameters. Its native call uses the existing compiler's
callability/arity checks, Func code pointer and closure environment, not a
second hand-written dynamic call implementation. Per-set C ABI shims call
that wrapper and preserve the earlier scalar/error/lifetime boundary.
The wrapper's synthetic call site is line2; errors inside target source retain
their original lines. Existing builtin errors can use line0, unchanged.

The selected name must be one ASCII identifier,1..128 characters, not a
module path or expression.1..32 same-arity sets of signed30-bit integer
arguments are accepted. Defaults are not supplied by this wrapper; target
runtime arity errors are captured. Only integer returns cross. Non-integer
returns stop without dereferencing/exporting them, as in the prior probe.
Captured call errors allow later calls; globals/imports/heap and mutations
persist. Initialization error skips calls. Private IR-key collision rejects.

The test compares ordinary reference calls for rebinding between calls,
closures with captured heap lists surviving allocation/GC, finally/error then
success, and zero/six arguments. It checks noncallable/arity/builtin error
capture and rejects invalid identifiers, oversized transport and empty lists.
Prior exact-key/sequence/status/return/ownership protocols remain unchanged.

This is still all-native target execution, with fixed wrapper shims and no
cold execution tier, hotness counter, dispatch-cell replacement, recompilation
or deoptimization. It is not a shared GC/value ABI, safe plugin API or a stable
public export system. The driver and target still share no language objects
or exception identity. Fatal exits, signals, unsafe faults, OOM/handler
overflow, extern rejection and unclosed file/resource restrictions remain.
No performance or completed tiered-JIT claim is made.
