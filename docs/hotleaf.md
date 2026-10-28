# Experimental hot pure-leaf dispatch (x86-64)

Build `selfhost/be/hotleaf_run.holy` with the pinned seed, then run
`RUNNER SOURCE THRESHOLD DIAGNOSTICS`. Ordinary interpreter execution does not
use this hook. The explicit runner counts calls by exact IR function identity,
compiles an eligible leaf only at its threshold, calls generated machine code
and resumes the hs interpreter. Source rebinding and aliases keep their normal
function identities. No performance claim is made.

Eligibility is deliberately narrow: a CFG of up to 16 blocks whose only
cycles are natural loops, nested or disjoint, up to six
parameters, constants/parameter loads, integer + - * % & | ^ << >> or unary minus/complement, integer comparisons for conditions, and statically uniform Int or Bool return.
No calls, globals/captures, mutation, allocation, print or exceptions
are compiled. Partially overlapping loops and side entries into a loop
remain interpreted. Bool, objects and values outside signed 30-bit fall back before
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

The CFG admission walk is topological, admits natural loops, nested or
disjoint, and rejects other cycles and unreachable blocks.
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

Bool constants are admitted as Bool-typed scalar values, enabling pure
predicate leaves that return true/false or a comparison on separate branches.
They lower to private machine 0/1 values and use the same guest-Bool result
boundary. Bool arithmetic and mixed Bool/Int returns remain refused. Six
additional literal/predicate/refusal cases bring the focused gate to 46.

Unary `not` accepts admitted Int or Bool temporaries and produces a Bool. It
uses scalar zero/nonzero truth tests; objects and Bool parameters still fall
back before native entry. Nested negation, comparison negation and branch
conditions preserve guest Bool identity. Bool arithmetic remains refused.
Seven additional scalar-not cases bring the focused gate to 53.

Bitwise `&`, `|`, `^` and unary `~` now admit Int temporaries only. Signed
30-bit operands are closed under these operations, including negative values;
the existing intermediate guard still applies. Bool arithmetic/bitwise inputs
remain refused, and non-Int or wider arguments fall back before native entry.
Eight further programs cover signed boundaries, complement, Bool refusal,
type fallback, guarded replay after multiplication and Bool predicate results,
for61 focused cases. Loops and shared objects remain outside admission.

Int shifts now enter the same pure-leaf subset. Native execution accepts only
counts0..29; negative or larger counts replay the original interpreted function,
including its count-range error. Left-shift intermediates fit signed64 bits
before the Int30 guard, and right shift is arithmetic for negative operands.
No x64 masked count is exposed. Eight programs check count and value boundaries,
Bool refusal/type fallback, negative arithmetic shift and intermediate overflow
replay, for69 focused cases. This is guarded scalar replay, not general deopt.

Int modulo now uses signed division plus a remainder-sign correction to match
the guest divisor-sign rule. A zero divisor replays the interpreted function
before native division. Int30 operands exclude machine signed-division overflow.
Eight programs cover all sign combinations, zero remainder, Int30 boundaries,
zero-divisor replay, Float/wide fallback, Bool refusal, multiple modulo sites
and earlier-intermediate overflow, for77 focused cases. Invalid Bool-modulo error
wording is checked by the separate interpreter type-error parity gate.

Equality/inequality between two statically Bool temporaries now stays native,
including comparison results and Bool literals. It uses the existing machine
0/1 representation and reconstructs guest Bool at return. Mixed Bool/Int
comparisons, Bool ordering and Bool arithmetic remain interpreted. Eight
programs cover equality truth tables, literals, branch conditions, mixed-kind
refusal, ordering refusal and Float-argument fallback, for85 focused cases.
Bool parameters are still outside native entry.

Acyclic scalar phi joins now support short-circuit `and`/`or` expressions.
Every predecessor must supply exactly one available value, all of the same
static Int/Bool kind. Native edges record their predecessor in a private
register; joins select the corresponding scalar slot. The existing purity and
range guards still apply, so replay cannot repeat guest effects. Nine programs
cover Int/Bool joins, nested joins, downstream use, skipped overflow paths,
actual overflow replay, mixed-kind refusal and type fallback, for94 focused
cases. Cycles, shared objects and general deopt remain excluded.

Local scalar bindings now extend across the acyclic CFG, through joins and
across reassignment. A local store records an existing Int/Bool temporary
available at the store as a new private version of the name; a load copies
the slot of the version visible on every incoming path. When arms bind the
local to different available temporaries of one static kind, loads resolve
through a synthetic phi lowered like any other join. No guest frame or heap
object is mutated: reassignment only shadows a private version. Parameter
writes start from a synthetic entry version of the raw argument, so rewritten
parameters and untouched arguments join through the same phis. Mixed-kind
join arms, a local bound on only some incoming paths, reads before binding
and effectful functions remain interpreted. Thirty-four programs cover
chained, cross-block, diamond, reassigned and parameter Int/Bool locals,
overflow replay, type fallback and refusals, for128 focused cases. Cyclic
control flow (loop compilation) and shared objects remain outside admission.

A single natural loop now stays native when the CFG has exactly one back edge:
a latch that jumps unconditionally to a header it is dominated by, where the
header's only other predecessor is the preheader outside the loop and no path
enters the loop body from outside it. A loop-carried Int/Bool local resolves
through a deferred-arm loop phi: the preheader arm records the version live on
entry, and the latch arm is filled from the version live at the latch and
kind-checked only after the latch block walks. Mixed-kind or unbound latch
arms, nested loops, back edges outside a single-header loop, side entries
and a preheader inside its own loop all refuse. Every intermediate inside the loop keeps the same
range guard, so overflow still replays the whole call in the interpreter. Nine
programs cover countdown, accumulation, zero iterations, loop-carried Bool,
break exit, in-loop overflow replay, argument type fallback and nested/two-loop
refusal, for136 focused cases. General cycles and shared objects remain
outside admission.

Disjoint natural loops and multi-latch loops now stay native. Back edges group
by header into one loop per header; a continue edge is a second latch of the
same loop, and loop phis resolve one kind-checked arm per latch, including the
self-arm that keeps a local unchanged on a continue path. Sequential loops,
independent accumulators, loops after branches and continues all compile.
Loops that partially overlap refuse. Seven programs cover
continue, continue with a loop-carried Bool, two and three sequential loops,
independent accumulators, a loop after a branch and mixed-kind latch refusal,
for142 focused cases.

Nested natural loops now stay native. A loop inside another loop shares its
blocks with the containing loop's body; the admission walk permits that when
one loop's blocks lie entirely inside the other's, while partially overlapping
loops still refuse. Each header keeps its own loop phis filled from its own
latches: a name stored in the inner loop counts as stored in the containing
loop, so both headers version it, while a name stored only in the outer body
flows through the inner header unchanged. Eight programs cover a nested
countdown, a multiplication-table sum, a zero-trip inner loop, inner
break/continue, triple nesting, inner-overflow replay and inner mixed-kind
latch refusal, for149 focused cases.
