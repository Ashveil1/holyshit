# agent — a small local agent written in pure holyshit

A from-scratch local agent core for the holyshit OS direction. It runs
entirely offline inside the hs runtime: no network, no external model,
no dependencies beyond the language itself.

## What it is today (v0.5)

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
- Wider dialogue, honest by construction: open questions
  (`how is X`, `why is X`, `how about X`, `tell me everything about X`,
  Thai `เกี่ยวกับ X`) read back the taught facts framed as
  `all i know about X is ...` - never a pretended answer to the how or
  why; Thai `<thing> คืออะไร` asks what-is; a small pleasantries layer
  (hello/how are you/thanks/bye, สวัสดี/ขอบคุณ) answers with fixed,
  visibly mechanical strings; `and X` recalls X, and `what else` /
  `anything else` continues the session topic.
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
  taught fact, and membership checks use a key set instead of walking
  the key list (see the benchmark section). Both are rebuilt on load
  and maintained on teach/forget; neither is persisted.
- Pure and portable: the core never does IO. `respond(state, line)`
  returns a reply, so the same core can later run freestanding in the
  kernel. Memory footprint is a few KB plus exactly what it was taught.

Commands: `remember <thing> is <fact>`, `remember <thing> is also <fact>`,
`no, <thing> is <fact>` (correction), `what is <thing>` (aliases:
`do you know`, `tell me about`, `who is`, `where is`),
`what do you know about <thing>`, `how is <thing>`, `why is <thing>`,
`when is <thing>`, `how about <thing>`, `tell me everything about <thing>`,
`เกี่ยวกับ <thing>`, `<thing> คืออะไร`, `and <thing>`, `what else`,
`anything else`, `what about it`, `<phrase> means <thing>`,
`forget <thing>`, `forget it`, `note <text>`, `notes`, `clear notes`,
`list`, `say <text>`, `help`, plus fixed pleasantries (hello/hi/hey,
how are you, thanks/thank you, bye/goodbye, สวัสดี, ขอบคุณ).
One trailing `?` or `.` is ignored.
Anything else gets an honest `i do not understand`.

## Hosted resource benchmark (A7 core, measured at 3ffc4b1 + keyset)

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

Current numbers (A7, keyset membership + word index; unchanged by the
A8 dialogue rules, which add only constant-time pattern checks - the
quick gate confirms), with the A5
pre-index baseline in parentheses where it differs:

| backend | facts | miss (A5) | recall (A6) | startup | peak RSS |
| --- | --- | --- | --- | --- | --- |
| interp | 0 | 1.8 ms (1.6) | - | 0.06 s | 22.7 MiB |
| interp | 1,000 | 4.6 ms (482) | 1.1 ms (1.8) | 0.31 s (0.06) | 23.7 MiB |
| interp | 10,000 | 43.5 ms (4,840) | 1.3 ms (8.0) | 2.59 s (0.15) | 33.9 MiB (31) |
| ir-x64 | 0 | 0.01 ms | <0.01 ms | <0.01 s | 21.5 MiB |
| ir-x64 | 1,000 | 0.01 ms (2.8) | <0.01 ms | 0.03 s | 21.5 MiB |
| ir-x64 | 10,000 | <0.01 ms (39.9) | 0.06 ms (0.10) | 0.38 s | 92.9 MiB (76) |

4 GiB probe (RLIMIT_AS on the child, 10k facts, mixed recall/miss
session): both backends complete - interp 2.8 s at 33.4 MiB peak (A5:
24.4 s), native 0.4 s at 92.8 MiB peak. Memory stays far inside a 4
GiB budget.

Honest readings:
- Misses and `did you mean` checks are word-index lookups now: ~100x
  on the interp route at 10k facts, and at native speed a miss costs
  what a recall costs. Thai substring questions still consult the
  (usually small) non-ASCII word list, and an all-Thai store keeps
  that scan proportional to its distinct non-ASCII words.
- Recalls no longer walk the key order list (keyset membership):
  8.0 -> 1.3 ms on interp at 10k facts. No O(number of taught facts)
  work remains on the ordinary question paths; association recall
  (`what do you know about`) is an intentional full scan.
- Costs of the derived structures: native peak RSS at 10k facts rose
  76 -> 93 MiB, and the interp route's cold startup rose to 2.6 s at
  10k facts because it rebuilds the index while loading (native: 0.38
  s). The on-disk format is unchanged - index and keyset are derived,
  never persisted.
- The held-out Thai/English dialogue (30 lines: 7 recalls incl. alias
  and Thai, 2 clarifications, 3 honest misses, 1 correction, 2
  pleasantries, 2 open questions, 2 topic chains) scores
  full marks on both backends at every stage - behavior did not move,
  only its cost. Small sample: a smoke check, not an accuracy study.

`tests/test_agent_bench.py` gates the dialogue check and a tiny-scale
smoke run in CI; the full run is manual.

## What it is not

It is not a language model and does not understand language. It cannot
answer anything it was not taught, cannot generalize, matching is
literal ASCII word matching plus non-ASCII substring matching,
"associations" are shared words between taught values, and its
clarifications are word-overlap guesses. Thai substring matches can be
loose in ways a speaker would notice (a short taught key can match an
unrelated longer word that merely contains it). Open questions get
taught facts read back, never an answer to the actual how/why/when,
and the pleasantries are fixed strings - not mood, not comprehension.
No reply should ever be
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
