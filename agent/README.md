# agent — a small local agent written in pure holyshit

A from-scratch local agent core for the holyshit OS direction. It runs
entirely offline inside the hs runtime: no network, no external model,
no dependencies beyond the language itself.

## What it is today (v0.4)

- An ordered pattern-rule matcher: a fixed set of command patterns is
  checked in order and the first match wins.
- A teachable memory: several facts per thing (`remember X is Y` sets,
  `remember X is also Y` adds), user-taught paraphrases
  (`<phrase> means <thing>`), kept in a plain JSON-serializable Dict
  (`agent/core.holy`), with hosted file persistence (`agent/store.holy`)
  and a terminal chat loop (`agent/repl.holy`).
- Teaching by correction: `no, X is Z` replaces the facts for X with Z
  (and updates the session topic), so a wrong or stale taught fact can
  be fixed without `forget` plus a fresh `remember`.
- A little dialogue context: it tracks the current topic and follows
  `what about it` / `forget it`; when a question misses but a handful of
  taught things overlap its words it asks `did you mean ...?` and
  understands `yes`, `no`, or the name; and it keeps short-term session
  `notes` that are never saved to disk.
- Association recall: `what do you know about X` answers with the taught
  facts plus others whose words overlap them (ASCII word match, glue
  words excluded) - string overlap, not understanding.
- Thai-aware matching: text is normalized without ASCII-izing, and
  non-ASCII tokens (Thai has no spaces or case) also match by
  substring - so `คนไทย` finds `ไทย` and `เมืองหลวง` finds `บางกอก`.
  The guard is deliberately independent of string length semantics:
  the interpreter counts characters while the compiled backends count
  bytes, so matching uses containment plus identity checks only, never
  a length threshold. Single ASCII letters never substring-match, so
  `c` still does not find `cat`.
- A derived word index: taught key words map to their keys, so misses
  and `did you mean` checks look up words instead of scanning every
  taught fact (see the benchmark section). The index is rebuilt on
  load and maintained on teach/forget; it is never persisted.
- Pure and portable: the core never does IO. `respond(state, line)`
  returns a reply, so the same core can later run freestanding in the
  kernel. Memory footprint is a few KB plus exactly what it was taught.

Commands: `remember <thing> is <fact>`, `remember <thing> is also <fact>`,
`no, <thing> is <fact>` (correction), `what is <thing>` (aliases:
`do you know`, `tell me about`, `who is`, `where is`),
`what do you know about <thing>`, `what about it`, `<phrase> means <thing>`,
`forget <thing>`, `forget it`, `note <text>`, `notes`, `clear notes`,
`list`, `say <text>`, `help`. One trailing `?` or `.` is ignored.
Anything else gets an honest `i do not understand`.

## Hosted resource benchmark (A6 core, measured at 5393ad5 + word index)

Measured with `tests/bench_agent.py` (repeatable: `--full`; synthesized
facts only). Method, per number: wall = `perf_counter` around the whole
process; cold startup = process wall for an immediate `quit` (loads and
re-saves the seeded store); latency = (session wall - startup) /
commands; peak RSS = the child process's own kernel-reported
`ru_maxrss` (wait4), per-process, not system-wide use. These are
HOSTED numbers (a Linux process running the hs runtime); future in-OS
(kernel-hosted) numbers are a separate milestone and must not be
conflated with these. Host: Linux 6.1 x86_64, glibc 2.35, Python
3.10.12 for the interp route.

Before/after the A6 word index (misses and `did you mean` checks used
to scan every taught key; A5 measured commit a6c628b, A6 re-measured
with identical scripts and method):

| backend | facts | miss before | miss after | recall | startup | peak RSS |
| --- | --- | --- | --- | --- | --- | --- |
| interp | 0 | 1.6 ms | 1.9 ms | - | 0.06 s | 22.5 MiB |
| interp | 1,000 | 482 ms | 6.1 ms | 1.8 ms | 0.06-0.32 s | 23.5 MiB |
| interp | 10,000 | 4,840 ms | 48.9 ms | 8.0-8.2 ms | 0.15 -> 2.61 s | 31 -> 33 MiB |
| ir-x64 | 0 | 0.01 ms | 0.01 ms | <0.01 ms | <0.01 s | 20.7 MiB |
| ir-x64 | 1,000 | 2.8 ms | 0.03 ms | <0.01 ms | 0.03 s | 20.7 MiB |
| ir-x64 | 10,000 | 39.9 ms | <0.01 ms | 0.10 ms | 0.41 s | 76 -> 92 MiB |

4 GiB probe (RLIMIT_AS on the child, 10k facts, mixed recall/miss
session): both backends complete - interp 3.0 s at 33.1 MiB peak (was
24.4 s), native 0.4 s at 92.3 MiB peak (was 0.6 s at 60.4 MiB). Memory
stays far inside a 4 GiB budget.

Honest readings:
- The index moved misses from ~0.5 ms/key scanned to word-dict lookups:
  ~80-100x on the interp route, misses at native speed (a 10k-fact
  miss costs what a recall costs). Thai substring questions still
  consult the (usually small) non-ASCII word list, and an all-Thai
  store keeps that scan proportional to its distinct non-ASCII words.
- Costs of the index: native peak RSS at 10k facts rose 76 -> 92 MiB
  (index lists), and the interp route's cold startup rose to 2.6 s at
  10k facts because it rebuilds the index while loading (native: 0.41
  s, unchanged). The on-disk format is unchanged - the index is
  derived, never persisted.
- Recall latency is unchanged (it never scanned candidates) and still
  walks the key order list once per question on the interp route (8
  ms at 10k facts) - conversational, but it is the next O(n) left.
- The held-out Thai/English dialogue (24 lines: 7 recalls incl. alias
  and Thai, 2 clarifications, 3 honest misses, 1 correction) scores
  full marks on both backends before and after - behavior did not
  move, only its cost. Small sample: a smoke check, not an accuracy
  study.

`tests/test_agent_bench.py` gates the dialogue check and a tiny-scale
smoke run in CI; the full run is manual.

## What it is not

It is not a language model and does not understand language. It cannot
answer anything it was not taught, cannot generalize, matching is
literal ASCII word matching plus non-ASCII substring matching,
"associations" are shared words between taught values, and its
clarifications are word-overlap guesses. Thai substring matches can be
loose in ways a speaker would notice (a short taught key can match an
unrelated longer word that merely contains it). No reply should ever be
read as more than pattern matching over taught facts.

## Direction (not a claim)

The long-term goal for this line is a conversational agent that chats
freely in natural language on a 4 GB machine at a tiny fraction of LLM
resource cost. That is the north star, not the current state. Stages
grow from this core — richer patterns, dialogue context, learned
associations — and each stage documents honestly what it can and cannot
do. This work is new and separate; it is not based on the paused `wnn`
research line and shares no code with it.

## Layout

- `core.holy` — the pure agent core (normalizer, rules, memory).
- `store.holy` — hosted JSON save/load (missing or corrupt file loads
  fresh).
- `repl.holy` — terminal chat loop; run `hs run agent/repl.holy` from
  the repo root. Memory persists to `agent-memory.json` on exit.

## Tests

`tests/test_agent_core.py` runs randomized conversation sessions against
an independent Python oracle of the same spec and requires byte-identical
transcripts on every execution route (reference interpreter, reference
IR, both x64 backends, the self-hosted seed and interpreter, and the gcc
native backend), plus hosted save/load roundtrips.
