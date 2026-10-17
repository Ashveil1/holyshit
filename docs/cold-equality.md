# Bounded cold container equality

The self-hosted cold IR executor now evaluates `==` and `!=` on flat scalar
Lists and Dicts with reference value semantics. Lists compare elementwise in
order; Dicts compare by key set and values, independent of insertion order.
Elements and values are compared with the existing scalar rules, so mixed
text/nontext pairs still reject even inside containers. Comparing a
container with a scalar, null or the other container kind yields false under
`==` (true under `!=`), matching the reference; mixed Str/container pairs
keep the existing mixed-text refusal. Aliases, slices and function
parameters compare by value like any other List or Dict record.

Equality allocates nothing, so it charges no list/dict/text budgets; the
ordinary instruction budget still bounds the walk. Ordering operators,
arithmetic and printing on containers keep their existing refusals: this
step covers equality only and claims no shared native objects or hot tier.

```hs
print [1, 2] == [1, 2]
print {"a": 1, "b": 2} == {"b": 2, "a": 1}
print [1] == {"a": 1}
# => true
# => true
# => false
```
