# Raw-ABI direct calls (IR x64 backend)

`docs/jit-unbox.md` keeps Int arithmetic raw *inside* a function, but every
call still paid the generic protocol: load the fn object, tag-check it,
arity-check it, push tagged arguments, indirect call, tagged result. For
call-dense integer code (recursive fib-style functions) that protocol - not
the arithmetic - is the remaining cost.

The backend now emits a **second, raw-ABI body** for qualifying module-level
functions and routes provable direct call sites to it:

- raw entry at a separate label (`hsIRraw_N`), tagged body unchanged at
  `hsIR_N` - every unprovable use (fn value, dynamic call, cross-module
  access) keeps working through the tagged body, so no escape analysis is
  needed;
- arguments arrive untagged in the same stack slots (`[rbp+24+8*i]`), the
  result is returned raw in `rax`;
- the call site skips the fn-object load, tag check and arity check and
  emits a direct `call` to the raw label.

## Analysis

A whole-program greatest fixpoint after frames are planned
(`_compute_rawabi`):

- **candidates**: module-level functions (defined by the entry thunk), name
  defined once per module, never rebound (`stvar`/`stglobal`/`setattr`/
  `unbind` of the name anywhere but its single initialisation);
- **shape** (per candidate, using the raw-variant `iraw`): every `return`
  carries a provably raw value, every assignment to a parameter stores a
  provably raw temp, no `unsafe` use of a parameter (`sload`/`sset`/
  `svarptr`/`unbind`), no nested `def` (`mkfunc` needs the fn object);
- **cap loads**: the raw body has no fn object (`r15`), so a captured
  reference (including the self-reference recursion goes through) is allowed
  only when its every use is the callee of a raw direct call - the load is
  then skipped entirely;
- **call sites** seed raw results when the callee resolves statically
  (same module, caller module-level, exact arity) and every argument is
  provably raw. Anything less keeps the generic tagged call.

Because parameters are only raw in the raw body, each qualifying frame
carries two analysis results (`iraw`/`ivars`/`rawcalls` for the tagged body,
`iraw_r`/`ivars_r`/`rawcalls_r` for the raw body); the emitter swaps them
around the raw body's emission.

## Scope and caveats

- Freestanding (kernel) images are excluded: the kernel ABI is not
  validated for raw-ABI calls yet.
- Raw values live in the conservatively scanned stack range. A raw Int only
  collides with the heap window for values around 2^43 and up; this is the
  same exposure the raw-Int unboxing already accepted.
- Same-module direct calls only; cross-module (`mod.fn`) and higher-order
  call sites keep the generic protocol.

## Performance

fib(33) ahead-of-time: 159 ms -> 112 ms (1.42x) on top of the unboxing
work. The win grows with call density.

Gate: `tests/test_ir_params.py` (outputs, errors, exit codes vs the tagged
semantics, including disqualification cases).
