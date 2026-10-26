# experiments/ — archived experiment scripts

One-off research scripts moved out of the ai/wnn root (cleanup, PR #290) so the
maintained hsml entry points stay visible. Code is byte-identical to its pre-move
state except a single sys.path bootstrap line at the top of each file (resolves
imports of ai/wnn modules like induce/cur7/text2prog without any install).

## The split

- **Scripts with a documented invocation contract stayed at ai/wnn root** (19 files:
  baby, baby2, baby3, baby3c, baby3h, baby4, cur1-cur6, text2prog, text2prog2/3/5/6/7/8).
  Their documented commands, e.g. `python3 cur6.py 0` or `python3 baby4.py`,
  work verbatim, unchanged, from ai/wnn. baby3 additionally needs an external
  API key (OR_KEY) as its docstring states — never executed in CI, no secrets in repo.
- **Everything else (43 files) lives here.** None of these had a documented
  command line; the historical LEDGER/BACKLOG citations of bare filenames are
  covered by the migration note in LEDGER.md.

## Running moved scripts

From ai/wnn, unchanged working directory and arguments:

    python3 experiments/<name>.py [args]

Outputs (/tmp files, logs/ files, own-dir caches) land where they always did;
verified for the log-writing b300r family.

## Verified reproductions after the move (2026-10-26)

- `experiments/b504.py` — EXACT LEDGER numbers: `wnn 0.188 | tf 0.163`, 11s wall.
- `baby4.py` (root, documented) — full 5-seed run to completion: class 20/20,
  CRITERION MET; chance-level arms 13/20 and 12/20 vs documented 11/20 and 10/20
  (both ~chance-10; wobble consistent with hash-seed sensitivity, qualitative
  verdict unchanged).
- `baby.py` (root, documented) — full run: true conditions 0.84/0.87 vs shuffled
  controls 0.06/0.16 (chance ~0.17).
- `text2prog.py 1` (root, documented) — P15 protocol runs to completion.
- `cur6.py 0` (root, documented) — bounded start verified (mul FOUND at 43s);
  full comb sweep is long-running by design, not re-run to completion.
- `experiments/cur2_test.py add,sub` — runs with args.
- `experiments/t5chain.py` — imports and starts correctly; the full LEDGER sweep
  (up to 1000 links) is long-running and was not re-run. Import/start only,
  not a completed reproduction.
