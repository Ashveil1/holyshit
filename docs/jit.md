# Experimental eager in-process execution

Linux x86-64 only. From the repository root:

```
export HSPATH="$PWD/selfhost:$PWD/selfhost/be"
export HSROOT="$PWD"
bootstrap/hs-hosted-x86_64 selfhost/be/jit_run.hs /tmp/hs-jit
/tmp/hs-jit tests/fib.hs
```

The native hs driver compiles source to machine code, relocates it into
owned code/data mappings and invokes it inside the same process. Code is
RW while copied, then RX. Data remains RW, never executable. No target ELF
is written or executed. The current emitter still builds a discarded ELF
byte list; avoiding that overhead is later work.

The generated process entry exits the driver. There is no return to the
compiler, code unloading, first-call compilation, type feedback, tiering or
deoptimization. Extern symbols are rejected, not silently left unbound.
Arguments are forwarded and the initial environment comes from Linux procfs.
Compilation diagnostics remain experimental. The existing `hs run` route is
unchanged. This path is not the default and has no startup-performance claim.

`tests/test_jitrun.py` builds the driver with the pinned hs compiler, then
checks runtime output, stderr and exit status against interp for recursion,
closures, lambda, floats, JSON, classes, exceptions, runtime errors and GC
stress. Separate memory/relocation tests check page permissions and lifetime.
These checks do not establish universal semantic or performance parity.
