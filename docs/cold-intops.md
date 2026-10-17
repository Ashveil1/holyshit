# Bounded cold Int30 modulo, bitwise and shift operators

The self-hosted cold IR executor now interprets `%`, `&`, `|`, `^`, `<<`,
`>>` and unary `~` on signed30-bit integers with reference semantics.
Modulo follows the reference (Python) sign rule: the result takes the
divisor's sign, and a zero divisor rejects with a division-by-zero refusal
on both build paths. Bitwise operators need Int operands (Bool rejects like
the other numeric operators), shift counts must lie in 0..63 like the
reference, and `>>` is an arithmetic shift. Unary `~` computes `-x - 1`.
Results must remain signed30-bit, so an overflowing `<<` rejects with the
same signed30-bit refusal as the existing arithmetic operators; the
reference's full i64 wrapping stays outside this subset.

The new operators allocate nothing and charge no list/dict/text budgets;
the ordinary instruction limit still applies. Float division (`/`) and
float operands remain unsupported, matching the existing boundary.
Operators on Lists, Dicts and mixed text pairs keep their existing
refusals.

```hs
print -7 % 3, 6 & 3, 5 ^ 3, 1 << 4, -16 >> 2, ~5
# => 2 2 6 16 -4 -6
```
