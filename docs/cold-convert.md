# Bounded cold conversions

The self-hosted cold IR executor now interprets `str(x)` and `int(x)` over
scalar values. `str` follows the reference display forms: Int decimal text,
`true`/`false`/`null`, and a Str argument returns the same value as an alias
with no new text produced. `int` follows the reference parser: Bool becomes
0/1, an Int passes through, and text parses after trimming, with `0x`/`0X`
hex forms accepted and invalid text refusing exactly like the reference.
Parsed results must fit the cold signed30-bit integer subset, so very large
text rejects rather than claiming wider integers. Converting Lists or other
records rejects, matching the existing rule that cold List printing is
unsupported.

`str` of an Int/Bool/null charges the produced text length to the cumulative
budget before publication (maximum1024 per value, 65536 per cold state,
never refunded); a Str argument charges nothing because it is an alias.
`int` produces only scalars and never charges. Existing instruction and
call-depth limits still apply.

```hs
print str(19) + "!"
print int("0x1A")
print int("40") + 2
# => 19!
# => 26
# => 42
```

The independent tests compare display forms, alias preservation, decimal/
hex/trimmed parsing, Bool/Int pass-through, round trips, function transport
and split/join composition against the reference interpreter. They test
record conversion refusals, invalid/empty text, null, out-of-subset results
and cumulative budget exhaustion through repeated conversions. Default CI
compiles the runner with the audited seed; --python-bootstrap is a local
diagnostic. Existing scalar20/List21/native15/text18/text-list10/slice14/
iteration11/search13/split-join15 gates remain. No shared native values/
roots, hot tier or performance claim is added.
