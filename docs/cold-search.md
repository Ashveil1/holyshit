# Bounded cold text search and membership

The self-hosted cold IR executor now interprets `find(s, sub)` (and the
`s.find(sub)` method form) plus `contains(container, x)` behind the `in` /
`not in` operators. `find` returns the first index of the substring or -1,
matching the reference. `in` over text is a substring check requiring a Str
needle; `in` over a cold flat List is element membership with reference
equality, including mixed Int/Bool/null/Str elements where cross-type
comparisons simply miss instead of rejecting. Searches over scalars reject,
and Dict lookup stays unsupported because cold Dicts do not exist.

Both searches produce only scalar Int/Bool results, so they add no new
budget rule: no text is produced and nothing charges beyond evaluating the
arguments themselves. Existing instruction, call-depth, text-byte and List
limits still apply.

```hs
s = "hello world"
print find(s, "world")
print "ell" in s
print 2 in [1, 2, 3]
# => 6
# => true
# => true
```

The independent tests compare find/method/empty-needle cases, substring and
`not in` checks, List membership across mixed element types (including
Bool/Int cross-equality), function transport and searches combined with
slices and iteration against the reference interpreter. They test wrong-type
find arguments, non-Str needles and scalar-container refusals. Default CI
compiles the runner with the audited seed; --python-bootstrap is a local
diagnostic. Existing scalar20/List21/native15/text18/text-list10/slice14/
iteration11 gates remain. No shared native values/roots, hot tier or
performance claim is added.
