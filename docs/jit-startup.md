# JIT startup gate (phase 4)

`hs prog.holy` must start small programs in under 50ms, end to end through
the installed native bundle. `tests/test_jit_startup.py` enforces the gate
where the budget is spent:

- **Driver**: the native JIT driver (bootstrap-compiled `selfhost/be/jit_run.holy`)
  runs small self-contained programs with a timed median under 50ms
  (measured locally at 11-13ms: hello, loop, closure, class fixtures).
- **Launcher**: `bin/hs` verified the audited driver against
  `EAGER_SHA256SUMS` on every run, costing ~31ms of the budget by itself.
  Verification is now memoized: a successful check is stamped in TMPDIR
  (keyed on the checksum file, stamp records the bundle path) and later
  runs skip the re-hash while the driver is older than the stamp. Any
  modification bumps the driver mtime and forces verification again, so a
  corrupted driver is still refused before execution (the
  `test_native_bundle` corruption gate is unchanged). An attacker able to
  reset mtimes bypasses the memo; the check guards accidental corruption,
  as the co-located checksum file always has.
- **Bare form**: `hs prog.holy [args...]` is accepted as `hs run prog.holy`.

Measured end-to-end through an installed bundle (`hs run` hello-world,
local sandbox): 47.7ms median before, 17.3ms after; launcher steady-state
overhead alone is ~6ms with a fake instant driver.

## Known gap: embedded runtime helpers

A program calling any `json_*` builtin makes the backend load
`runtime/json.holy` (~450 lines) through the full parse/IR/verify/compile
pipeline on every run, adding ~270ms. Such programs are outside the timed
gate for now (json output stays covered by correctness fixtures and the
byte-parity corpus). Caching or precompiling embedded runtime helpers is
follow-up work for a later phase.
