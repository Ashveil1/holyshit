# Bounded cold text slices

The self-hosted cold IR executor now interprets Str slices with the reference
clamped-bounds semantics. Missing bounds default to the ends, negative bounds
count from the end, both clamp into the string, and an empty range produces
the empty string. Non-Int bounds (including Bool) reject, matching the
reference `slice index must be Int` refusal. This covers slicing only;
repetition, iteration, methods/conversions/formatting and Unicode stay
unsupported.

Slices work on text values only here. List slices are covered in
[Bounded cold flat List slices](cold-list-slice.md), and slicing an
Int/Bool/null scalar rejects. Existing List ownership, creation/slot budgets
and aliases stay unchanged.

Every non-empty slice charges its complete result length to the same
cumulative byte budget as constants and concatenation (maximum1024 per value,
65536 per cold state, never refunded); empty slices charge nothing. Charges
validate before publication, so a failed charge leaves accounting unchanged.
Existing instruction/call-depth limits still apply.

```hs
s = "hello world"
print s[0:5]
print s[-5:]
print s[3:3] + "!"
# => hello
# => world
# => !
```

The independent tests compare basic/missing/negative/clamped/empty bounds,
variable and expression bounds, function transport, chained slices and empty
text against the reference interpreter. They test List/scalar slice refusals,
Bool and non-Int bounds, cumulative budget exhaustion and free empty slices.
Default CI compiles the runner with the audited seed; --python-bootstrap is a
local diagnostic. Existing scalar20/List21/native15/text18 gates remain. No
Unicode, shared native values/roots, hot tier or performance claim is added.
