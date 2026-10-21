# bench - hs vs CPython

Run: `python3 bench/run.py [name ...] [--timeout seconds]`
Each case is a `bench/<name>.holy` + `bench/<name>.py` pair printing identical
output (the script checks this). It compares `hs.py xbuild` (direct ELF, no
gcc) against CPython; CI runs it nightly and keeps the results as an artifact.

## Baseline at v0.6.30 (measured 2026-10-12)

Machine: 2-core sandbox, CPython 3.10.12 (absolute numbers vary by machine; read the ratios)

| Case | CPython | hs xbuild | Faster by | MB py | MB hs | Notes |
|---|---|---|---|---|---|---|
| fib(32) | 0.35 s | 0.07 s | 5.2x | 9 | 9 | repeated function calls |
| loop 20M (add/mod) | 1.38 s | 0.22 s | 6.4x | 9 | 9 | pure int |
| strings (3M append+join+split) | 0.74 s | 0.36 s | 2.1x | 444 | 406 | |
| alloc (5M `"abc"+str(i)`) | 1.05 s | 0.60 s | 1.7x | 9 | **687** | no free on x64 - memory grows forever |
| dict (200k insert + iterate) | 0.10 s | **>20 s (timeout)** | **~1000x slower** | - | - | linear-scan key lookup (`emit_dict_helpers`) |

First-ever measurement (not in `bench/`): dict 200k insert = 117.5 s vs CPython 0.096 s

## Conclusions

- int/function-call work is already ~5-6x faster than CPython
- The two spots to fix before claiming "faster than Python": a real hash dict and an allocator that can free (see `ROADMAP.md` phase 1)
- interp.py (tree-walk) numbers: fib(22) 436 ms vs CPython 15 ms - it is the behavior reference, not the fast path

## After adding GC (P1, branch p1-gc)

Conservative mark-sweep on IR->x64 (`gcrt.py`): collects only at safe points
(function entries / loop heads). roots = stack + data segment + `unsafe alloc` blocks (pinned). The `x64`/kernel runtime is unchanged.

| bench | before | after |
|---|---|---|
| alloc (5M strings) | 0.60 s, 687 MB | 0.45 s, 9-16 MB |
| fib / loop / dict | - | no significant change |
| strings (3M live strs) | 0.32 s | 0.66 s (16B header + bitmap + GC scan) |

Tests: `tests/x64/gc_stress.holy` (diffed against interp), `gc bound` in
test_x64 (alloc bench < 50 MB), and running all suites with a GC every 4 KB
passing (used during development).

## Compact immutable strings (2026-10-14)

Removing unnecessary extra slack from x_str_at/x_str_cat reduces the
3-million-string benchmark's local peak RSS from 469 MB to 377 MB.
Nine alternating baseline/candidate runs on the same host measured
medians 0.580149s and 0.520208s (about 10% lower runtime). All outputs
match. This is a local result, not a cross-machine speed guarantee.
The GC arena-cache experiment was discarded after it did not improve
alternating-run medians. Allocation churn remains bounded by GC.
