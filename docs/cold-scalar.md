# Self-hosted cold scalar IR executor

```sh
export HSPATH="$PWD/selfhost:$PWD/selfhost/be"
export HSROOT="$PWD"
bootstrap/hs-hosted-x86_64 selfhost/be/cold_scalar_run.holy /tmp/hs-cold-scalar
/tmp/hs-cold-scalar tests/fib.holy
/tmp/hs-cold-scalar tests/fib.holy --stats
```

This executor is written in .holy and compiled once with the native compiler.
It parses/lowers a target to verified IR and interprets that IR with dictionaries
for frames/temporaries and an instruction loop. It does not import the native
backend, publish executable target mappings or compile the target into machine
code. This is actual cold execution of a small subset, not relabeled eager
whole-program compilation. There is no hot tier or cold/native transition yet.

Supported: signed30-bit Int, Bool and null constants; integer +,-,*, comparisons;
scalar equality; negation/not; scalar branch conditions, jumps, simultaneous
phi assignment; variable/global stores; module-level functions, dynamic aliases/
rebinding, recursion and exact-arity calls; one scalar per print; return. While,
break/continue, if/elif and short-circuit expressions lower to these operations.
No nested functions/captures, classes, imports, source collections/strings,
floats/division, builtins, unsafe/FFI, exceptions/finally or shared native objects.
Unknown instructions/operators/terminators or unsupported constants anywhere
in the module reject during whole-module preflight before target side effects,
even in unreachable code. Runtime operand violations can occur after effects.

All arithmetic operands/results must remain signed30-bit integers. Other
comparisons/arithmetic are outside this executor's subset even where the full
language permits them. This restriction bounds transport and avoids claiming
full integer/float semantics. Source-function values are private executor
records, never native target Func objects. Function values cannot be printed,
compared or used as scalar branch conditions. Dynamic calls remain interpreted.
Local-before-assignment is rejected rather than falling back to a global.

The CLI allows one million IR instruction/terminator steps, counting each
executed instruction (including phi) and each terminator; it permits64 live
call frames and at most256 functions. The library accepts a step limit1..10M.
Exhaustion raises an executor diagnostic, no retry/rollback. A state starts
only once, even after failure. Depth restores on every exit. Per-function
entry counts include module entry and are bounded by execution; --stats emits
total steps and these counts after normal completion, not argument values.
Counters do not compile anything or change dispatch. CLI without --stats adds
no diagnostic stdout after successful target output.

Errors use `cold scalar:` diagnostics, not yet source-line/error parity with
interp.py. Failures are not caught inside target code. Prior output/mutations
are not undone. Bounds limit execution, not parser memory, total heap allocation
or an adversarial sandbox. The executor runs in its own hosted runtime and GC;
it shares no target language objects/roots with the existing native probes.

`tests/test_cold_scalar.py` compares supported outputs with the independent
Python reference: recursion, while/break/continue, local/global state, rebinding,
branches, booleans/null and short-circuit phi. It checks whole-module refusal
before print, runtime limits, exact fib counts, unbound-local behavior, budget
and single-start/depth cleanup. CI builds the executor with the audited native
seed; explicit --python-bootstrap is a local diagnostic build route only.

This is the first executable cold-subset scaffold, not stage3 completion.
Full value ownership/root and exception contracts, classes/closures/aliasing,
FFI, hot-function dispatch, guards/deoptimization and measured performance
remain. The existing eager/AOT routes and Python reference stay unchanged.
