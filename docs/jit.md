# Experimental eager in-process execution

Linux x86-64 only. One-command route:

```
scripts/run-jit-native.sh tests/fib.hs
```

This verifies the pinned seed, builds an isolated native hs JIT driver,
runs the source with arguments, forwards the exit status and removes the
temporary driver. It needs shell/checksum utilities and procfs, not Python
or gcc. Driver compilation happens on every invocation and can be slow.
It is deliberately separate from `hs run`, with no fallback or cache.

For repeated experiments, build the driver once from the repository root:

```
export HSPATH="$PWD/selfhost:$PWD/selfhost/be"
export HSROOT="$PWD"
bootstrap/hs-hosted-x86_64 selfhost/be/jit_run.hs /tmp/hs-jit
/tmp/hs-jit tests/fib.hs
```

The native hs driver compiles source to machine code, relocates it into
owned code/data mappings and invokes it inside the same process. Code is
RW while copied, then RX. Data remains RW, never executable. No target ELF
is written or executed. The sections-only emitter does not pack an intermediate ELF.

The generated process entry exits the driver. There is no return to the
compiler, code unloading, first-call compilation, type feedback, tiering or
deoptimization. The driver loads explicit prebuilt shared-library paths/sonames with the host
libc loader and binds every extern GOT slot before publishing code. Missing
libraries/symbols fail before target execution. Handles stay live until process
exit. Bare short names such as "m" remain outside the native driver subset;
use "libm.so.6" or an explicit path. Relative paths use the source directory.
Symbols bind through their declared library handle. Conflicting owners of the
same C symbol are rejected; fflush is reserved to libc for output ordering.
This is not a self-written loader.
Safe Ints retain the x64 62-bit limit. Out-of-range results can fail with
exit 97 instead of the reference interpreter's 64-bit behavior. There is no
interpreter fallback.

Arguments are forwarded and the initial environment comes from Linux procfs.
Compilation diagnostics remain experimental. The existing `hs run` route is
unchanged. This path is not the default and has no startup-performance claim.

`tests/test_jitrun.py` builds the driver with the pinned hs compiler, then
checks runtime output, stderr and exit status against interp for recursion,
closures, lambda, floats, JSON, classes, exceptions, runtime errors and GC
stress. Separate memory/relocation tests check page permissions and lifetime.
These checks do not establish universal semantic or performance parity.

## Compare with AOT

```
python3 bench/jit.py /tmp/hs-jit --runs 5
```

The benchmark alternates JIT and AOT runs and checks exact output/status on
every run. Its untimed AOT setup uses the native hs compiler. JIT timing
includes parsing/IR/emission/relocation/execution; AOT timing includes only
execution. Building the driver is excluded. Numbers vary by machine.

A local five-run median check on 2026-10-14 measured (JIT / AOT seconds):
fib 0.1023 / 0.0734, loop 0.2617 / 0.2283, dict 0.0775 / 0.0593,
alloc 0.3653 / 0.3508, strings 0.5039 / 0.5002. Outputs matched.
The eager path does not meet the roadmap's within-10%-of-AOT criterion
across those cases. A separate nine-run alternating hello-world check
measured 10.77 ms median for the already-built eager driver and 43.11 ms
for interp, including source compilation in the eager measurement. Neither
result establishes whole-language performance or first-call JIT completion.
