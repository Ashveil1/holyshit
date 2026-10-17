# Bounded cold print

The self-hosted cold IR executor now interprets print with any number of
arguments, matching the reference: values join with single spaces and one
newline ends the line, so bare print emits an empty line. Scalar display
forms are the reference forms - Int decimal, `true`/`false`/`null`, and text
as itself - evaluated left to right. Lists, functions and other records
still reject, keeping the existing rule that cold List printing is
unsupported. Printing charges no text bytes, as before.

```hs
x = 5
print "x is", x
print 1 + 2, "sum"
# => x is 5
# => 3 sum
```

The independent tests compare mixed-type lines, bare print, expression and
variable arguments, function transport, loops, and List-argument refusals
against the reference interpreter, including preserved earlier output when a
later argument rejects. Default CI compiles the runner with the audited
seed; --python-bootstrap is a local diagnostic. Existing scalar20/List21/
native15/text18/text-list10/slice14/iteration11/search13/split-join15/
convert17/range14 gates remain. No shared native values/roots, hot tier or
performance claim is added.
