# Bounded cold ASCII text

The self-hosted cold IR executor now accepts printable ASCII Str constants
and newline/tab/carriage-return bytes, each at most1024 bytes. Non-ASCII and
other control bytes reject during whole-module preflight, including unreachable
constants, before target effects. This is a declared subset, not Unicode or
full string compatibility.

Supported operations are assignment/pass/return, concatenation with another
Str, same-type equality/ordering, truth/not and short-circuit conditions,
len (including builtin alias), negative integer indexing and one-value print.
Strings are immutable host-runtime values owned by the cold executor; aliases
keep the old value when another variable is rebound. No raw target pointers
or shared native objects are created. The native bridge remains Int30-only.

Mixed text/nontext binary operands reject even for equality, rather than
claiming full language cross-type comparison. Repetition,
methods/conversions/formatting and Unicode remain unsupported. Iteration is
covered in [Bounded cold iteration](cold-iteration.md). Slices are
covered in [Bounded cold text slices](cold-text-slice.md); source string
elements in Lists remain unsupported. In particular string-valued ternary arms currently lower
through singleton Lists and therefore reject at runtime. Existing flat Lists
still contain only Int30/Bool/null; their ownership/budgets remain unchanged.

Each execution of a string constant charges its length, every concatenation
charges its complete result length, and indexing charges one byte. Maximum
string length1024 and cumulative charged bytes65536 per cold state, never
refunded. Aliases/pass/return/printing/len/comparison do not charge extra source
bytes. Charges validate before allocation/publication; failed charges leave
accounting unchanged. This is a conservative logical source-byte budget, not
exact heap bytes or host allocation counts: parsing, IR, preflight validation,
compiler/executor infrastructure, host GC and temporary validation/iteration
storage remain outside it. Existing instruction/call-depth limits still apply.

Runtime operand/budget errors may follow previous effects and do not undo
them. Diagnostics remain executor-specific, not source exception/line parity.
No text flows across the explicit isolated-native boundary. No shared GC,
hot selection, tiering, speed or full stage-completion claim is added.

The independent tests compare reference outputs for immutable alias rebinding,
function transport, concatenation, ASCII controls, truth/short circuit, builtin
len alias, same-type comparisons and negative indexing. They test preflight
non-ASCII/length refusal before print, bounds/type/operators/List element/store
refusals, per-result/cumulative budgets and unchanged counter on failed charge.
Default CI compiles runner and library harness with the audited seed;
--python-bootstrap is a local diagnostic. Existing scalar20/List21/native15
gates remain, replacing only their old unsupported-string preflight example
with an unsupported float now that text is accepted.

## Flat List element extension

[Text elements in flat Lists](cold-text-list.md) now supersede the earlier
string-element/string-ternary refusal. Nested Lists and List-valued ternaries
remain unsupported. Text production budgets and native Int30-only transport
stay unchanged.
