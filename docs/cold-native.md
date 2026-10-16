# Explicit cold/native scalar bridge experiment

`cold_native_run.holy COLD_SOURCE BRIDGE_NAME NATIVE_SOURCE GLOBAL_NAME ARITY`
preflights/creates the cold state first, prepares one isolated native module
and runtime-argument global shim, initializes it once, binds an explicit name
in the cold globals and runs the cold IR executor. Interpreted code computes
arguments, calls native code, receives an immediate integer and resumes
interpreted instructions/frames. This is a real narrow cold-to-native-to-cold
return boundary, not hot-function compilation, dispatch replacement or tiering.
The native helper is a separate explicitly chosen module compiled eagerly;
its globals are not the cold module's globals.

`coldscalar.bind_scalar_bridge` is a trusted host-library extension installed
only before a state's single start. The source cannot construct such a record
or choose arbitrary callbacks. Source assignment can shadow/rebind the name;
ordinary alias and interpreted function dispatch otherwise remain. The bridge
validates every argument as Int30, not Bool/List/function, before calling its
host handler, and validates the result as Int30. Per-binding4096 call attempts
bound the added callback work; attempts count before invoking the handler,
including native errors. Source instruction/depth budgets remain, but do not
bound the time spent in an arbitrary native helper. Invalid transport does
not call native code. Binding identifiers are1..128 ASCII identifier chars.
Trusted library callers must supply well-formed state/name/handler/context.

`coldnative.bind` adapts the existing live dynamic native state to this hook.
It copies only validated immediate argument words into target-owned writable
slots. Results are copied scalar integers, not native target heap pointers;
no cold List/function/global object is shared. Native closures/rooted captures
remain solely target-owned and can survive target GC. Native global lookup
happens on every invocation, including native rebinding.

A native language error becomes a copied `cold native:` diagnostic with its
native line. It is not a reconstructed source exception object/finally state
in the cold interpreter. Cold execution stops, call depth cleans up, and prior
effects remain. A trusted library caller can inspect the failure then run a
new cold state against the still-live native module. No native-to-cold callback
or reentrant/concurrent entry is supported. Existing fatal exits/signals/OOM,
unsafe corruption/non-returning native code remain outside recovery.

The CLI releases native heap then executable image in finally after controlled
cold success/failure; initialization language errors skip cold execution and
also release. Preparation/fatal/unsafe failures do not claim cleanup. Library
callers retain the same explicit initialize-before-call, heap-then-image
release obligations as the native probe. No pointer validation/public plugin
ABI, shared value/root/exception ABI, sandbox or performance claim is added.

Tests compare recursive/result-dependent calls, cold List mutation around
scalar-only calls, target closures surviving GC, native rebinding and later
cold shadowing, and zero args against an independent reference wrapper. They
reject Bool/List transport, non-Int/out-of-width results, native/init errors,
bridge call budget and unsupported cold IR before native initialization effects.
A library test confirms native error then fresh cold-state success, invalid
transport without incrementing the native counter, depth cleanup, late-binding
rejection and released image state. Default CI builds both runner and harness
with the audited seed. Existing cold scalar/List and native dynamic/function
gates remain. This is still not completion of shared-runtime stage2/3.
