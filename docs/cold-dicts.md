# Bounded cold flat Dicts

The self-hosted cold IR executor now owns bounded flat Dicts: literals with
Str or signed30-bit Int keys (Bool and other types reject, matching the
reference key rule) and Int30/Bool/null/Str values. Dicts are explicit
interpreter-owned records like cold Lists, never raw host objects: assigning,
passing and returning preserves identity, so aliases see each other's
writes. Indexing reads values, missing keys reject, and `d[k] = v` inserts
or replaces after key/value validation, leaving the target unchanged on
failure. `len`, `has`, `keys`, `values`, `in` membership and `for k in d`
(insertion order, like the reference) all work; keys/values and iteration
yield ordinary charged cold Lists. Nested containers, record values,
slicing, printing, ordering and arithmetic on Dicts remain unsupported;
Dict equality is covered in
[Bounded cold container equality](cold-equality.md).

Each literal charges one creation plus one slot per written pair, and each
new key inserted by assignment charges one slot; replacement charges
nothing. Limits mirror the List model: at most4096 pairs per Dict, 1024
creations and65536 cumulative slots per cold state, validated before
publication and never refunded. These are separate counters from the List
budgets. Existing instruction, call-depth and text limits still apply.

```hs
d = {"a": 1}
d["b"] = 2
print len(d), d["b"], has(d, "a")
for k in d:
  print k
# => 2 2 true
# => a
# => b
```

The independent tests compare literal/index/insert/replace, Int and mixed
keys, membership, keys/values order, iteration, truthiness, aliasing and
function transport against the reference interpreter. They test missing-key,
Bool/record key, wrong-container, arithmetic/print/nested-value and slice
refusals plus the4096-pair and creation-budget boundaries. Default CI
compiles the runner with the audited seed; --python-bootstrap is a local
diagnostic. Existing scalar20/List21/native15/text18/text-list10/slice14/
iteration11/search13/split-join15/convert17/range14/print11 gates remain.
No shared native values/roots, hot tier or performance claim is added.
