# Bounded cold iteration

The self-hosted cold IR executor now interprets `for` loops over text values
and cold flat Lists through the existing iterseq/index/len lowering. Iterating
a Str yields its one-character strings exactly like repeated indexing, and
iterating a flat List yields its elements with preserved aliases. Empty
sequences run zero iterations. Break/continue, nested loops, sliced or
concatenated text, and iteration inside functions behave as in the reference
interpreter. Scalars and other values reject as not iterable, matching the
reference refusal. Dict key iteration stays unsupported because cold Dicts
do not exist.

Iteration adds no new charge rule: each text element extraction is the
existing one-byte index charge, so a full pass over a string charges its
length to the same cumulative budget (1024/value, 65536/state, never
refunded). List element extraction remains free, as indexed access already
is. Existing instruction, call-depth, creation and slot limits still apply.

```hs
t = ""
for ch in "abc":
  t = t + ch + "."
print t
# => a.b.c.
```

The independent tests compare character/element loops, empty sequences,
break/continue, sliced/concatenated sources and function transport against
the reference interpreter. They test not-iterable scalar refusals and
cumulative budget exhaustion through repeated iteration. Default CI compiles
the runner with the audited seed; --python-bootstrap is a local diagnostic.
Existing scalar20/List21/native15/text18/text-list10/slice14 gates remain.
No shared native values/roots, hot tier or performance claim is added.
