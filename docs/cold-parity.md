# Cold/reference parity audit

The parity audit suite locks the cold executor's contract: anywhere inside
the documented subset, the seed-built cold driver and the independent Python
reference produce byte-identical standard output and exit status; anywhere
outside it, the cold driver refuses with a nonzero exit instead of silently
diverging. The battery spans the combined feature set in single programs:
Int30 arithmetic/modulo/bitwise/shift, text and its slices/searches,
split/join, flat Lists and Dicts with slices/equality/iteration, functions,
globals, recursion, module-level comprehensions and non-capturing lambdas,
struct-only classes (construction, field get/set), multi-value print,
conversions, range, membership, abort-only raise/assert and mixed control
flow with break/continue.

The documented exclusions refuse cleanly (the reference behavior is pinned
alongside, so a silent cold acceptance fails the audit): floats and `/`
division, nested functions and captures (including function-level
comprehensions and lambdas), class methods (struct-only classes work),
try/except/finally and exception objects, imports, side-effecting builtins
(file/OS/network/JSON/process), float conversion, container
printing/ordering/arithmetic, nested containers (including List/Dict-arm
ternaries), mixed text/nontext comparison, and receiver string methods
(which the reference itself rejects). String repetition, scalar indexing,
non-Str raise and container ordering reject on both sides.

```hs
xs = [i * 2 for i in [1, 2, 3]]
print xs[2], len(xs), xs == [2, 4, 6]
# => 6 3 true
```
