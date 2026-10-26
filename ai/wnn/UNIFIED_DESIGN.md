# Unified conversational prototype (b592) - design sketch (awaiting go-ahead)

One class, `hsmlChat`, wiring the measured components:

1. DEFINITIONS FIRST (B-591/b): user-taught pattern rules checked before
   anything else. One-shot: pair + 1 variable-marking question. Latest
   wins; definitions can shadow trained grammar (must be surfaced).
2. SHELL (B-588): intent gate (tau_hi=tell, low=ask, mid=guess+confirm),
   teach-then-answer on teach intents, honest limits on unknown answers,
   in-band corrections update the mapper, rate-limited.
3. RECENCY (B-590): anaphora resolved to most recent mention; ask only on
   zero candidates; recency also feeds answer inference.
4. PERSISTENCE (B-582, separate labeled probe): facts + definitions +
   mapper weights saved/loaded; fresh-process chat continues. OFF unless
   the user opts in (privacy rule); measured as its own probe.

Learned components: WNN mapper (correctable in-band), taught fact/rule
inventory. Supplied: aligner/compiler, recency policy, gate thresholds,
rate limit. All labeled as such in reports.

Measurement: v1 18-turn scenario + v2 reference extension; questions
(yes/correction split), actions, fabricated count; whole-runtime RSS and
wall time via Watchdog. Expected burden reduction from definitions vs
B-588 is the key number.
