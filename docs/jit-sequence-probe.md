# Sequential independent runtime experiment

```sh
export HSPATH="$PWD/selfhost:$PWD/selfhost/be"
export HSROOT="$PWD"
bootstrap/hs-hosted-x86_64 selfhost/be/jit_sequence_probe.holy /tmp/hs-sequence
/tmp/hs-sequence tests/fib.holy tests/t_exceptreturn.holy tests/fib.holy
```

The diagnostic accepts1..32 source paths. It compiles each source into a
fresh independent image/runtime, invokes it once, copies any captured language
error into driver memory, destroys its target heap/image and proceeds to the
next source in the same live driver process. A captured status1 does not stop
the sequence; parse/compile/driver errors and fatal target exits still do.
The process exits0 after captured outcomes, so this is not a normal run CLI.
No automatic retry or parallel execution is added.

Every source starts fresh, including globals, imported module initialization,
closures, exception handler state and target allocator metadata. Running the
same source twice does not reuse its old exports, code or heap. The common
`jitboundary.finish` helper owns invoke, copied-error extraction and teardown;
the existing single-source status probe calls the same helper and retains its
markers and checkpoint protocol. The original return probe is unchanged.

`--checkpoints` is diagnostic only. Each cycle prints its image range, waits
at the existing heap-before/heap-after teardown checkpoints, prints outcome
and release markers after image release, then waits before the next compile.
The test reads `/proc/PID/maps` at these stops to prove heap ranges and image
exist before teardown, heap ranges disappear first, and image range is gone
before the next cycle starts. Addresses can be reused by later mappings; the
test checks each cycle at its own stops, not historical address uniqueness.
Ordinary mode prints no addresses and waits for no input.

The test alternates success, dynamic errors with finally, closures, GC stress
and an empty module, repeating an import-mutating source to verify fresh module
state. Each cycle's target output and captured error match independent Python
reference runs. The driver survives eight cycles including errors and its
copied error bytes remain valid after target teardown. This is a finite
lifecycle proof, not an unbounded memory/latency benchmark or a claim that all
driver allocations are freed after every compile.

The [status probe's limits](jit-status-probe.md) still apply: fatal exits,
OOM, handler overflow, signals, unsafe metadata corruption and extern calls
are not recovered/supported. Target-opened file descriptors and arbitrary
resources are not closed; only current gcrt-owned mappings and image mappings
are destroyed. Process-wide side effects outside those mappings can persist.
This is not repeated invocation of one module, a shared runtime, object/GC-root
interop, individual-function ABI, cold execution tier or hot-code dispatch.
No performance claim is made.
