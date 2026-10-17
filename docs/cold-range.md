# Bounded cold range Lists

The self-hosted cold IR executor now interprets `range(n)` and `range(a, b)`,
returning a cold flat List of consecutive Ints from the start (default 0,
inclusive) to the stop (exclusive), empty when the range is inverted or zero.
Arguments must be cold signed30-bit integers; Bool, text, extra or missing
arguments reject. The result is an ordinary cold List: indexing, replacement,
append, len, membership and iteration all work, and `for i in range(n)` is
now the idiomatic counted loop in the cold tier.

Each range List uses the existing List budgets: one creation and one slot
per element, validated before publication, so ranges beyond4096 elements
reject and the cumulative65536-slot budget still applies. No new budget rule
is added; range produces no text.

```hs
total = 0
for i in range(5):
  total = total + i
print total
print len(range(2, 6))
# => 10
# => 4
```

The independent tests compare counted/offset/empty/inverted ranges, element
access, replacement, append, membership, nested loops, break/continue and
function transport against the reference interpreter. They test non-Int and
Bool arguments, wrong arity, over-limit lengths and the exact4096-element
boundary. Default CI compiles the runner with the audited seed;
--python-bootstrap is a local diagnostic. Existing scalar20/List21/native15/
text18/text-list10/slice14/iteration11/search13/split-join15/convert17
gates remain. No shared native values/roots, hot tier or performance claim
is added.
