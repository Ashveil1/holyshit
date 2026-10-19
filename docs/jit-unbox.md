# Raw-Int unboxing (IR x64 backend)

The IR x64 backend (`selfhost/be/be.holy`, `GenIR`) tags every Int value
(`(v << 2) | 1`) and untags it again around every arithmetic op. For programs
that are mostly integer loops this tag/untag dance dominates the generated
code.

The backend now proves which SSA temps and which variables can only ever hold
Ints and keeps those values **raw** (untagged) in their stack slots, boxing
only where a value crosses into a generic consumer (call argument, return,
print, container store, variable that escapes analysis, ...).

## Analysis

A combined greatest-fixpoint per function, computed after all frames are
planned:

- **iraw temps**: integer constants, `bin` results over `{+,-,*,%,<<,>>,&,|,^}`
  with both operands raw, unary `neg`/`~` of raw, and phi nodes whose arms are
  all raw. `/` is excluded because Int/Int yields Float.
- **ivars (int-owned variables)**: `stvar` targets where every stored value is
  provably Int and the variable never escapes analysis: not a parameter, not
  captured by a closure, not touched by `unsafe` (sdecl/sset/svarptr/sload),
  never `del`ed, never stored via `stglobal`, and - for module-level
  variables of the entry module - never referenced from any other function or
  module in the whole-program image.

Raw loads feed raw ops; every generic consumer goes through the normal
`_load`, which re-boxes (tag_box) raw temps on the way out, so semantics are
preserved by construction at every boundary.

## Semantics preserved

Every raw op replicates the exact checks of the generic tagged path:

- `+`, `-`, `*`: the same overflow trapping (`int_ovf` / 62-bit range error),
- `%`: Python-style sign of the divisor and `division by zero` at the same
  line,
- `<<`, `>>`: shift-count range errors, 62-bit truncation for `<<`,
- comparisons and `==`/`!=` on two raw Ints emit a direct `cmp` + `setcc` and
  box the Bool result,
- branches on a raw Int test zero directly (same truthiness),
- mixed-type operands fall back to the fully generic path with unchanged
  error messages.

Gate: `tests/test_ir_unbox.py` - outputs, error text and exit codes are
byte-identical against the tagged reference behavior, including closures,
exceptions, for-loops, dict/list/string mixing and `unsafe` interplay.

## Measured (sandbox, warm JIT driver vs old-backend AOT, medians of 7)

| case | old JIT | unboxed JIT | note |
|---|---|---|---|
| loop (20M add/mod) | 337 ms | 188 ms | 1.8x faster |
| alloc (5M strings) | 414 ms | 401 ms | slight win |
| fib(32) | 105 ms | 100 ms | params still boxed |
| dict / strings | - | - | unchanged (runtime-bound) |

## Not done yet

- Function parameters stay tagged (interprocedural specialization is a
  separate step; it would unbox `fib`-style recursion),
- values still round-trip through stack slots (no register allocation),
- `%` by a constant still emits `idiv` (strength reduction possible).
