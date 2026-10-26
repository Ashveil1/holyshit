# experiments/ — archived experiment scripts

One-off experiment and reference scripts from the LEDGER research log
(B-300..B-519 era), moved here from the parent directory on 2026-10-26.
Nothing here is imported by the staying tree; the staying tree (hsml.py,
chat.py, b521-b559 harnesses, regress_skills.py) does not depend on this
directory.

## Running an archived script

From the `ai/wnn` directory (the same working directory as before the move):

```sh
python3 experiments/<name>.py [args]
```

Old form (pre-move): `python3 <name>.py` — the file now lives one directory
down; the working directory, `logs/` output location, and arguments are
unchanged. Scripts that import staying modules (`induce`, `cur7`) carry a
one-line path bootstrap at the top so this works from any directory.

Verified reproductions after the move (2026-10-26):
- `python3 experiments/b504.py` — reproduces LEDGER B-504 numbers exactly
  (wnn 0.188 | tf 0.163, ~10-17 s wall)
- `python3 experiments/text2prog.py` — P15 synonym-mapping protocol runs
- `python3 experiments/cur2_test.py <names>` — cur-family test runs
- `python3 experiments/b300r.py` — writes logs/b300r_run.log as before

## Output locations (isolation)

- Scripts write only to `/tmp` (cur1/cur4/cur6/baby3h), their own directory
  (baby3 cache), or their own file under `logs/` (b300r_run.log). Nothing
  here writes to state files read by the staying harnesses.
- baby3/baby3h call an external API (need OR_KEY); they are kept for the
  record, not part of the local reproduction set.

## LEDGER references

LEDGER.md verdicts cite these scripts by their original bare filenames
(e.g. `b504.py`, `baby4.py`, `t3lex.py`); those citations now resolve to
`experiments/<name>.py`. Log-file citations (`logs/...`) are unchanged.
