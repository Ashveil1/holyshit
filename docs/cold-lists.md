# Interpreter-owned flat scalar Lists

The self-hosted cold executor now supports a bounded List subset: literals of
Int30/Bool/null elements, len, append, negative indexing, indexed mutation,
truth/not, aliasing and passing/returning the same List through interpreted
functions. `len`/`append` load as ordinary builtin values when unshadowed;
module globals and function locals take precedence. Scalar-only printing and
comparison remain; nested/cyclic Lists, object elements, slices, iteration
builtins and arbitrary source objects remain outside the subset.

Source Lists are explicit private records with an items array, distinct from
executor function and builtin records. Assigning, passing or returning a List
preserves the record identity; indexing/setindex/append operate on its items.
Scalar/index/size validation happens before a write. Invalid elements or
indexes leave that operation's target unchanged, without undoing earlier
program effects. Returned Lists stay inside interpreted execution; they are
never target-native pointers or exported objects in another runtime.

All List storage is held by the hosted executor's existing runtime/GC.
Frames, temporaries and globals reference the same private records, so mutable
aliases survive function boundaries. No custom tracing/root registration is
added and no claim is made about sharing with the separate native target
runtime. Native/cold object interoperability is still unresolved.

Per-state limits are4096 elements per List,1024 cumulative List creations
(including empty), and65536 cumulative inserted slots across literals/append.
These budgets do not replenish when a List becomes unreachable, providing a
finite allocation-work boundary rather than relying on GC timing. Indexed
replacement consumes no new slot. Checks charge before publishing/growing.
Existing step/depth/function limits and single-start state still apply.
The accounting bounds logical source slots, not exact bytes, temporary host
arrays, parser memory or an adversarial sandbox.

Unsupported source constants/instructions still preflight-reject. Flatness,
operand types, index/size and allocation budget are runtime checks and can
fail after earlier target output. Diagnostics retain the executor-specific
error/line limits; exceptions in target code are still unsupported. Ternary
expressions lower through singleton Lists and now work for supported scalar
arms without eager evaluation of the unchosen branch.

The tests compare independent reference outputs for mutation through aliases,
function argument/return identity, scalar elements, append/len aliases and
shadowing, loops, ternary/default fresh List semantics and List truth. They
check bad/nested element/index/callability/size/creation-budget cases, unchanged
state after a rejected store, and cumulative slot budget without overcharge.
The prior scalar suite remains, dropping only its former List-preflight test
because List IR is now supported; unsupported strings/division/imports/try and
nested functions still reject before effects.

This is a cold-only value-ownership step, not full collection semantics, shared
GC/value ABI, native transition, hot compilation or a performance claim.

[The text-element extension](cold-text-list.md) now admits existing bounded
immutable ASCII Str in flat Lists, without copying/recharging text bytes on
alias insertion. This supersedes the Int/Bool/null-only element restriction,
not the nested/cyclic/function/native-object restrictions above.
