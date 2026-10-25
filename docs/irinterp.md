# IR interpreter tier (written in holyshit)

`selfhost/be/irinterp.holy` executes the IR from `irbuild` directly, in hs, with no
code generation and no Python. Program values are plain hs values, and the
structure follows the Python reference executor in `ir.py`. Runtime errors are
re-lined to the failing instruction, so stderr matches `interp.py`.

`selfhost/be/irinterp_run.holy SOURCE [args]` is the driver. Build it with the
pinned seed: `bootstrap/hs-hosted-x86_64 selfhost/be/irinterp_run.holy OUT`.

Supported: the dynamic core (variables, closures, calls, lists, dicts, slices,
iteration, try/except/finally, raise, print), `import` (including dotted module
paths and package shells) with `attr`/`setattr` on modules, and the builtins
`len str int float range append split find join has contains keys values`,
plus the file, env, argv, input, json and system builtins. The import graph is
walked statically at preflight (parse + irbuild only, no execution), so modules
using unsupported ops are still refused before any output; missing, broken or
circular imports reproduce interp.py's rc-1 errors at runtime.

Refused up front (rc 3, `error: irinterp: unsupported ...`, before any output):
unsafe/`s*` ops, `ffi`, and builtins outside the
subset when the program uses one without binding it. These are the next steps.

`tests/test_irinterp.py` runs every `tests/*.holy` through `interp.py` and the
driver and compares exit code, stdout and stderr byte for byte (67 programs
match; 17 are pinned as refused; `t_load64` is a documented 62-bit vs 64-bit
Int divergence).

Known limits: the callable records (`hs_ir_fn`, `hs_ir_builtin`) are dicts, so a
user dict with those reserved keys would be mistaken for a callable.

On arm64, the test builds a native driver with `a64build.py` as stage0,
then executes each program in the hs interpreter. The driver uses the shared
Linux syscall exit path, with no dynamic libc dependency. On x86-64, test the
same AArch64 path explicitly with:

```sh
python3 tests/test_irinterp.py --arm64-qemu /path/to/qemu-aarch64
```

Both paths must preserve all 85 corpus classifications (including refusals and
the documented Int-width divergence). Neither route introduces a JIT.

## Python-free source command

On Linux x86-64, `scripts/run-interp-native.sh SOURCE [args...]` checks the
pinned compiler seed, builds the hs interpreter in a temporary directory and
executes the source through it. No Python/gcc is used. Source paths/arguments
may contain spaces; imports resolve from the source directory and HSPATH.
The command preserves stdout, program arguments, environment and exit status,
and removes its temporary driver on controlled success/error. Unsupported
programs refuse up front with rc 3, without switching to Python or AOT.
This rebuilds the interpreter per launch; it is not a cached or JIT command.
The shell launcher currently uses the x86-64 seed, while native arm64
interpreter execution remains available through its tested stage0 build path.

## Builtin argument counts

The hs interpreter checks all 31 supported builtin argument counts before
indexing the guest argument list or invoking a host builtin. It no longer
ignores extra arguments, reports host index errors for missing arguments, or
accepts a prompt for the no-argument `input()` builtin. Errors retain the
source call line and match the reference for caught and uncaught calls.

The parity gate includes 124 wrong-count cases through builtin aliases,
covering too few/too many arguments and both exception paths, in addition to
the existing 85 corpus classifications. This is argument-count parity, not a
claim that every builtin type/error edge case is covered.

Float conversion rejects nonnumeric, nonstring guest values before entering
the host conversion helper. Null/List/Dict/callable errors retain their guest
type names instead of accidentally converting the host error text. Twenty
additional alias conversion cases cover caught/uncaught failures and existing
valid Bool/Int/Float/Str conversions, for 229 total parity classifications.

Executed module frames and synthetic package shells belong to each interpreter
state. Two states importing the same module now initialize independent guest
globals and function registrations. Imports repeated within one state still
reuse that state's module. The regression interleaves two states and checks
counter results 2, 2, 3. Parsed-module metadata remains a process cache; this
change does not promise source reload, concurrent execution or a sandbox.

## Variable binding state

Frame binding metadata is now separate from guest values. A guest string equal
to the former `u0004IRUNBOUNDu0004` marker is an ordinary string in assignments,
parameters, globals and containers. Unbinding an exception name clears its
binding flag instead of storing a guest-visible sentinel. All interpreter-owned
frame writes use the same binding helper. The parity gate adds five focused
cases, including exception-name cleanup, for235 total classifications. Existing
hot-leaf53/53, profiling11/11 and native interpreter command5/5 gates remain.
This does not fix the separately documented callable/module-record collision
limit or establish a sandbox.
