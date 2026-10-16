# Isolated native outcome experiment

```sh
export HSPATH="$PWD/selfhost:$PWD/selfhost/be"
export HSROOT="$PWD"
bootstrap/hs-hosted-x86_64 selfhost/be/jit_status_probe.holy /tmp/hs-status
/tmp/hs-status tests/fib.holy
```

The diagnostic generates one independent target runtime with a root native
exception handler around `hs_main`. A normal module returns status0. A
language error that reaches this root returns status1 instead of terminating
the driver. Inner target try/except/finally and rethrow still run normally.
The root consumes one of the existing 256 handler slots, leaving at most255
for target code while active. Fatal runtime exits, handler-stack overflow,
unsafe memory faults, OOM and process signals are not recovered.

The existing backend emits its exception runtime only if IR contains a
handler/raise. The probe adds one private, uncalled IR helper with an empty
try/except solely to request that runtime for otherwise handler-free targets.
It is not an executed function or a cold execution tier. A private IR-name
collision is rejected, not silently replaced. Original target lines remain
unchanged. There is no compiler/backend/seed semantics change.

On root error the shim copies raw message-pointer/byte-length/line metadata
from the existing exception value stack into an image-local mailbox, drops
the active value and returns across the saved C ABI boundary. Before any
target memory is released, the driver copies message bytes into its own heap.
It then destroys target GC arenas/bitmaps/table and code/data mappings, and
only afterward prints the copied outcome as JSON. No target Str, closure,
object or pointer is returned as a reusable shared language value.

`JIT OUTCOME [0, null]` means normal completion; status1 includes the copied
message and its original source line. `JIT STATUS RESUMED` is a diagnostic
marker, not target output. The probe process exits successfully for either
captured outcome; a target status1 is deliberately not a CLI exit-status
contract. Parse/compile errors and extern rejection remain driver errors.

`--heap-checkpoints` reuses the explicit stdin teardown checkpoints from the
[ownership experiment](jit-return-probe.md). Tests inspect `/proc/PID/maps`
while the driver lives, proving target-owned mappings present before and
absent after error cleanup, then verify the copied dynamic message prints
correctly after teardown. Ordinary mode emits no addresses and waits for no
input. The original return probe remains unchanged in behavior, using the
same boundary implementation with error capture disabled.

This is a one-shot isolated module outcome, not shared exception identity,
a resumable individual-function ABI, repeated module execution, resource
unwinding across runtimes, GC-root interoperability, a cold tier or hot-code
dispatch. Extern code stays rejected. Heap ownership trusts the current gcrt
layout; unsafe corruption is outside the boundary. Target-opened files and
other arbitrary resources are not closed. No performance claim is made.
