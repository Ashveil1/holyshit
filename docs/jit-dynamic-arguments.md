# Runtime scalar arguments to one native shim

`jitboundary.prepare_dynamic(source,global_name,arity)` prepares one private
native global-call shim with0..6 arguments and an isolated target module.
Unlike the prior argument-set probes, it does not emit different shim code
for every value set. `dynamic_outcome(state,arguments)` validates a List of
exact-arity signed30-bit integers before writing tagged immediate words to
private target writable data, then invokes that same entry. Bool is rejected.
The shim loads the current slot words on each call and uses ordinary native
global/closure dispatch. No executable code is modified, no pointer-bearing
source value crosses, and no mutable driver List is installed in target heap.

This remains a private diagnostic, not a public plugin ABI or cold/hot tier.
The caller initializes the target using `scalar_outcome(state,state[1],false)`
and calls only after successful initialization. After the final controlled
return, release target heap first, then image. Existing fatal/OOM/signals,
unsafe corruption and source side-effect limits remain. State is opaque and
trusted: do not edit its slots, call before initialization or after heap
release, or interleave/reenter/concurrently invoke it. Released images reject
before reading/writing target memory. This live-state check is not ownership
protection against a forged/corrupted state. Native calls may block forever.

Argument checks finish before the first slot write/native call. Invalid
arguments leave the previous slots and target globals untouched. Native
language errors return copied message/line metadata through the existing root
handler; prior native effects persist and later calls may continue. Integer
results use the existing tagged-result check, not object export or new full
integer semantics. Non-integer results remain a fatal diagnostic limitation.
There are no target exceptions reconstructed in a cold interpreter yet.

`jit_dynamic_probe.holy SOURCE GLOBAL_IDENTIFIER JSON_ARGUMENT_SETS` drives
1..32 sequential calls for diagnostics. Arity comes from the first set; later
checks happen immediately before each call, after module initialization and
any earlier calls, not whole-input preflight/rollback. Library callers can
compute subsequent arguments from earlier results without preparing new code.
The existing exact-key/fixed-set APIs keep their behavior.

Tests compare native global rebinding, closures/rooted captures surviving GC,
finally/error-then-success, six/zero args and call errors with the independent
reference. A separate library test uses results8 then20 as subsequent arguments
to the same native entry, verifies unchanged tagged slots33/41 and call count
through eight rejected transports, then result24 and dead-image rejection.
Default CI compiles both driver and library harness with the audited native
seed; --python-bootstrap is a local diagnostic. Prior function/dispatch tests
remain. This is preparation for a scalar cold/native boundary, not that
boundary itself, shared values/roots, hot compilation or a speed claim.
