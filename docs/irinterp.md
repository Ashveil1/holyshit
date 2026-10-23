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
driver and compares exit code, stdout and stderr byte for byte (68 programs
match; 16 are pinned as refused; `t_load64` is a documented 62-bit vs 64-bit
Int divergence).

Known limits: the callable records (`hs_ir_fn`, `hs_ir_builtin`) are dicts, so a
user dict with those reserved keys would be mistaken for a callable.
