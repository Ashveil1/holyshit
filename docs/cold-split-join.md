# Bounded cold split and join

The self-hosted cold IR executor now interprets `split(s)` / `split(s, sep)`
(including the `s.split(...)` method form) and `join(sep, list)`. Split
follows the reference exactly: no separator splits on whitespace runs and
drops empties, a separator keeps empty fields, and an empty separator
rejects on both sides. The result is a cold flat List of text elements with
the usual ownership, aliases and List budgets, so it works with iteration,
membership and indexed access. Join requires a Str separator and a flat List
whose elements are all Str, matching the reference refusals. The receiver
method form of join rejects on both sides because the separator must come
first.

Split charges the sum of its element lengths to the cumulative text budget,
and join charges its complete result length, both before publication like
concatenation and slices (maximum1024 per value, 65536 per cold state, never
refunded). The created List charges the existing creation and slot budgets.
Existing instruction and call-depth limits still apply.

```hs
words = split("the quick fox")
print len(words)
print join("-", words)
# => 3
# => the-quick-fox
```

The independent tests compare separator/whitespace/empty-field splits,
method forms, join shapes, round trips, function transport, membership and
slice composition against the reference interpreter. They test wrong-type
arguments, non-Str join elements, empty separators, receiver-join refusal
and cumulative budget exhaustion through repeated splits. Default CI
compiles the runner with the audited seed; --python-bootstrap is a local
diagnostic. Existing scalar20/List21/native15/text18/text-list10/slice14/
iteration11/search13 gates remain. No shared native values/roots, hot tier
or performance claim is added.
