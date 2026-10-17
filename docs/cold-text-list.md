# Cold ASCII text elements in flat Lists

Cold flat Lists now accept the already supported immutable bounded ASCII Str
values alongside Int30/Bool/null. Literal, append and indexed replacement use
the existing constant-value validation rather than integer-only validation.
List alias identity stays mutable, while retrieved text remains immutable:
replacing a List element does not change an earlier text alias. Passing and
returning the same List through interpreted functions preserves this behavior.

Existing text validation/budget and List creation/slot budgets remain separate.
Producing a text value charges its bytes as before; placing an existing value
in a List or replacing a slot does not copy or charge text bytes again. Literal
slots/append still consume the cumulative List slot budget; replacement does
not. Invalid elements/indexes still reject before mutation. Nested Lists,
cycles, functions/builtins/bridge values, List printing/comparison and native
object sharing remain unsupported. The native bridge remains Int30-only.

String-valued ternary arms now work through the parser's existing lazy
singleton-List lowering: only the chosen arm evaluates. List-valued ternary
arms still require a nested temporary List and therefore reject. This feature
does not change lowering or claim general object-valued conditionals.

The tests compare immutable element aliases, mutable List aliases across
calls, append/replacement, fresh defaults and lazy string ternaries with the
independent reference. Nested/self/function/List-valued ternary refusals remain.
A library test verifies unchanged old text after a failed store and exact
separate creation/slot/text accounting after alias reuse. The prior cold text
suite drops only its obsolete refusal of a valid string List; its other18
gates remain, as do the21 List and15 native-bridge gates. Default CI uses the
audited seed for runner and harness; --python-bootstrap is diagnostic.

No Unicode, shared native values/roots, new GC, exception parity, hot tier,
performance or completed-runtime claim is added.
