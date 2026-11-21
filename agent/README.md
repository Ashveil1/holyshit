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

## Hosted resource benchmark (v0.4 core, commit a6c628b)

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

| backend | facts | cold startup | peak RSS | recall | honest miss |
| --- | --- | --- | --- | --- | --- |
| interp (reference) | 0 | 0.06 s | 22.5 MiB | - | 1.6 ms |
| interp (reference) | 1,000 | 0.06 s | 23.3 MiB | 1.8 ms | 482 ms |
| interp (reference) | 10,000 | 0.15 s | 31.0 MiB | 8.0 ms | 4,840 ms |
| ir-x64 (native) | 0 | <0.01 s | 20.7 MiB | <0.01 ms | 0.01 ms |
| ir-x64 (native) | 1,000 | 0.03 s | 20.7 MiB | <0.01 ms | 2.8 ms |
| ir-x64 (native) | 10,000 | 0.41 s | 76.4 MiB | <0.01 ms | 39.9 ms |

4 GiB probe (RLIMIT_AS on the child, 10k facts, mixed recall/miss
session): both backends complete - interp in 24.4 s at 30.9 MiB peak,
native in 0.6 s at 60.4 MiB peak. Memory is far inside a 4 GiB budget;
miss latency on the interp route is the real scaling wall.

Honest readings:
- Memory footprint is small and grows slowly: interp adds ~8.5 MiB for
  10k taught facts over its 22.5 MiB interpreter floor; the native
  image has a ~20.7 MiB runtime floor and holds 10k facts in ~40-56
  MiB more (its store representation is less compact).
- Recalls stay fast at every scale (the fact Dict does the work).
- Honest misses and `did you mean` checks scan every taught key with
  no index: cost grows linearly (~0.5 ms/key interp, ~0.004 ms/key
  native). At 10k facts a native miss is 40 ms, an interp miss is
  ~4.8 s. Retrieval without an index is the known limitation, now
  quantified.
- The held-out Thai/English dialogue (24 lines: 7 recalls incl. alias
  and Thai, 2 clarifications, 3 honest misses, 1 correction) scores
  full marks on both backends at every scale - but it is small; treat
  it as a smoke check of behavior, not an accuracy study.

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
