# Bounded cold raise and assert

The self-hosted cold IR executor now interprets the `raise` terminator and
the parser's `assert` lowering with abort-only reference semantics.
`raise "msg"` aborts the program with the message, propagating through
calling functions; bare `raise` rejects (no active exception, matching the
reference, since try/except stays outside the subset) and non-Str values
reject with `raise wants Str`. `assert cond` aborts with `assertion failed`
when the condition is falsy and `assert cond, msg` aborts with the evaluated
Str message; a passing assert has no effect. Standard output produced before
the abort is preserved.

This is not exception handling: there are no exception objects, no
try/except/finally and no catching, so a raise always terminates the cold
program like the reference does without a handler. Raises allocate nothing
and charge no budgets beyond the ordinary instruction limit.

```hs
assert 2 > 1, "math broke"
print "fine"
# => fine
```
