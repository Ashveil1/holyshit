# Bounded cold flat List slices

The self-hosted cold IR executor now interprets slices of flat scalar Lists
with the reference clamped-bounds semantics. Missing bounds default to the
ends, negative bounds count from the end, both clamp into the List, and an
empty range produces a new empty List. Non-Int bounds (including Bool)
reject, matching the reference `slice index must be Int` refusal. The result
is an independent copy: mutating it never touches the source List, and the
source is never consumed. Slicing Dicts, Int/Bool/null scalars and records
still rejects, as does printing a sliced List directly (print remains
scalar-only). Text slices are covered in
[Bounded cold text slices](cold-text-slice.md).

Every slice charges one List creation plus one slot per copied element to
the same budgets as literals and append (at most4096 elements per List,
1024 creations and65536 cumulative slots per cold state, validated before
publication and never refunded); an empty slice charges the creation only.
Existing instruction, call-depth and text limits still apply.

```hs
xs = [1, 2, 3, 4]
ys = xs[1:3]
print len(ys), ys[0], ys[1]
ys[0] = 99
print xs[1], ys[0]
# => 2 2 3
# => 2 99
```
