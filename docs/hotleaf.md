# Experimental hot pure-leaf dispatch (x86-64)

Build `selfhost/be/hotleaf_run.holy` with the pinned seed, then run
`RUNNER SOURCE THRESHOLD DIAGNOSTICS`. Ordinary interpreter execution does not
use this hook. The explicit runner counts calls by exact IR function identity,
compiles an eligible leaf only at its threshold, calls generated machine code
and resumes the hs interpreter. Source rebinding and aliases keep their normal
function identities. No performance claim is made.

Eligibility is deliberately narrow: an acyclic CFG of up to 16 blocks, up to six
parameters, constants/parameter loads, integer + - * or unary minus, integer comparisons for conditions, and statically uniform Int or Bool return.
No calls, globals/captures, mutation, allocation, print, loops, phi nodes or exceptions
are compiled. Bool, objects and values outside signed 30-bit fall back before
native entry. Every native intermediate is range-guarded; a guard failure
returns a private sentinel and interprets the original function. Replay is safe
only because the admitted leaf has no effects. A sentinel cannot be an admitted
result. Products of two admitted operands fit signed 64-bit intermediates.

Code uses RW-to-RX pages; argument slots remain in a separate RW page. The
native body does not allocate, call a runtime, retain values or expose pointers.
Only copied immediate integers cross the boundary. Contexts bound sites/images;
image-cap overflow interprets instead of evicting live code. Release occurs in
finally on controlled success/error; released contexts reject use. Fatal signals,
unsafe corruption and process termination remain outside cleanup guarantees.
The diagnostic file reports compiles, native successes and guard/type fallbacks.

The emitter is written in hs with the existing own assembler, not LLVM or an
external code generator. It is x86-64 only. This is a real but restricted
interpreter-to-native-to-interpreter hot-leaf experiment, not a general method
JIT: no shared heap objects/roots/exception ABI, recursion in native code,
on-stack replacement, type-specialized object operations or general deopt.

The CFG admission walk is topological and rejects cycles/unreachable blocks.
Each use must be available on every incoming path; definitions are unique.
Internal comparison values are Bool and may steer branches or return as a Bool,
but cannot enter integer arithmetic. All return paths must agree on one static
Int/Bool result kind; mixed-result functions remain interpreted. Native Bool
results are reconstructed as guest Bool values, not exposed as integer 0/1. Integer truth
tests are allowed. The total instruction and code-page budgets remain bounded.

The scalar result gate includes all six comparison operators, branch-selected
Bool results, printed/JSON Bool identity and arithmetic rejection after native
return. A non-Int argument still falls back before native entry. This does not
admit Bool parameters, shared objects or a general tagged-value ABI.
