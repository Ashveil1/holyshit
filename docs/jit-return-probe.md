# One-shot native module-return experiment

This is the first bounded step toward a resumable runtime. Unlike the eager
`_start` entry, a generated shim calls `hs_main` and returns to its driver on
normal completion. The driver prints a return marker and releases the image's
RX code and RW data mappings. C ABI callee-saved registers and stack are saved
and restored. Target argv is empty; its environment comes from Linux procfs.

```sh
export HSPATH="$PWD/selfhost:$PWD/selfhost/be"
export HSROOT="$PWD"
bootstrap/hs-hosted-x86_64 selfhost/be/jit_return_probe.holy /tmp/hs-return
/tmp/hs-return tests/fib.holy
```

This is a diagnostic probe, not a general runner or a tiered JIT. It creates
one independent target runtime. No values, closures, GC roots or exceptions
cross from target to driver. Uncaught errors still terminate the process;
extern code is rejected. It skips the process-entry signal/alternate-stack
setup. Generated heap arenas live until process exit, so do not use this for
repeated module loading or long-lived unload/reload. Only code/data image
release is tested. A returning entry is not a memory-lifetime solution.

`tests/test_jit_return.py` builds the driver with the audited native seed and
compares recursion, closures, lambda, floats, JSON, classes, finally/unwind,
GC stress, environment, errors and extern rejection with the reference.
`--python-bootstrap` is an explicit local diagnostic route; it runs the same
native driver behavior but is not evidence of native compiler bootstrap.

Next work: define shared value ownership and GC roots, a non-exiting exception
status, and a stable function ABI. A real cold tier and hot-function dispatch
must wait for those transition guarantees. Existing eager, AOT and native
bundle behavior is unchanged. No speedup or completed tier is claimed.

## Owned target-heap experiment

An explicit `/tmp/hs-return SOURCE --release-heap` additionally destroys the
normally returned target's GC arenas, start bitmaps and arena table, then
releases its code/data image. The default stays process-owned. No target
object may escape: this is destruction of an isolated runtime, not a shared
GC or a production module loader. It relies on the current audited gcrt
metadata layout and is not safe against arbitrary unsafe corruption.

`--release-heap-checkpoints` is a diagnostic route: it prints owned ranges,
waits on stdin, destroys them, prints a checkpoint and waits again. The test
reads `/proc/PID/maps` at both stops, including multi-arena GC stress, to
prove the mappings are actually gone before process exit. Ordinary release
mode does not emit address lists or wait for input. Unmap failures stop and
must not be retried as a whole destruction operation.

Only this runtime's GC memory and code/data image are owned by this route.
Target-opened file descriptors and other resources are outside it. Uncaught
errors still terminate the process. Repeated invocation, shared objects and
exception recovery remain future work. This does not complete stage2 or add
hot-code compilation, and it carries no performance claim.
