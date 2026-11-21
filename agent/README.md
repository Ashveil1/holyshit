# agent — a small local agent written in pure holyshit

A from-scratch local agent core for the holyshit OS direction. It runs
entirely offline inside the hs runtime: no network, no external model,
no dependencies beyond the language itself.

## What it is today (v0.7)

- An ordered pattern-rule matcher: a fixed set of command patterns is
  checked in order and the first match wins.
- Learning from usage, smallest honest version: for every content word
  in every taught fact (key or value) it counts which other content
  words appear alongside it, across all facts. Two uses, both honestly
  framed: a miss with several `did you mean` candidates orders them by
  co-occurrence with the asked words (was: insertion order), and a
  clean miss on a word that shows up in taught values answers
  `i was never taught X, but from how you used it, X seems related to
  A, B` (top 3 by count, ties by first-seen order). It is counting,
  not understanding: it can say two words appeared together, never
  what the relation is. Thai words participate as whole tokens (there
  is no segmenter). The counts are derived state, rebuilt on load like
  the word index - nothing new is persisted and the v4 format is
  unchanged. Corrections and forgets un-count what they remove.
- Relations and small inference: taught facts whose values take a
  recognized shape also record a relation edge - `remember paris is in
  france` records (paris is-in france), `remember cat is an animal`
  records (cat is-a animal, article kept), `remember cat has whiskers`
  records (cat has whiskers), and Thai `remember แมว อยู่ สวน` /
  `remember ลิง คือ สัตว์` record the same is-in / means edges.
  `is paris in europe` then answers by transitive closure over those
  edges and shows the chain it used (`yes: paris is in france, france
  is in europe`); a miss is open-world honest (`not that i know`,
  never a claimed `no`). `where is paris` walks the is-in chain
  outward, `what does X mean` answers from taught means-edges plus a
  small hard-coded self-knowledge set defining the agent's own
  relation words (mean/is-in/is-a/has - documented as hard-coded, not
  learned), and `<phrase> means <free text>` now defines a phrase
  directly instead of erroring on unknown targets. `means`,
  `หมายความว่า` and `คือ` write the same edge. Thai questions get
  Thai-framed replies (`แมว อยู่ไหน` -> `แมว อยู่ สวน`).
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
- Relation edges (`rels`) persist in the v5 store format (which adds
  the `forgotten` tombstone list); pre-v5 files re-derive edges from
  their fact shapes on load, once, and the built-in self-knowledge
  edges are never persisted.
- A bare `X is Y` teach whose value matches no known shape still files
  a kind-of edge and says so (`(filed as a kind-of)` in the reply) -
  deliberately shallow: `sky is blue` files blue as a kind of sky.
  `is X Y` asks over the is-a chain without needing an article; Thai
  yes/no questions `<X> เป็น <Y> ไหม` and `<X> คือ <Y> หรือไม่` answer
  over the same chains, and a trailing `?` forces question mode
  (`apple means fruit?` checks instead of teaching).
- Bounded self-knowledge: `what do you know` counts taught things and
  names the 5 most recent, `what did you forget` lists the tombstones
  it keeps (last 20), `what did we talk about` replays the session log
  (last 10 events, this session only, never saved). Each answer
  states its own bound.
- Pure and portable: the core never does IO. `respond(state, line)`
  returns a reply, so the same core can later run freestanding in the
  kernel. Memory footprint is a few KB plus exactly what it was taught.

Commands: `remember <thing> is <fact>`, `remember <thing> is also <fact>`,
`remember <thing> has <part>`, `remember <thing> เป็น <kind>`,
`no, <thing> is <fact>` (correction),
`what is <thing>` (aliases: `do you know`, `tell me about`, `who is`),
`is <thing> in <thing>`, `is <thing> a <kind>`, `is <thing> <kind>` (bare is-a question),
`where is <thing>`
(is-in chain), `what does <thing> mean` (means relation + built-in
self-knowledge), `what do you know about <thing>`, `how is <thing>`,
`why is <thing>`, `when is <thing>`, `how about <thing>`,
`tell me everything about <thing>`,
`เกี่ยวกับ <thing>`, `<thing> คืออะไร`, `<thing> หมายความว่าอะไร`,
`<thing> อยู่ไหน`, `<thing> เป็น <thing> ไหม`,
`<thing> คือ <thing> หรือไม่` (Thai yes/no questions), `and <thing>`,
`what else`,
`anything else`, `what about it`, `<phrase> means <thing>`,
`forget <thing>`, `forget it`, `what do you know`,
`what did you forget`, `what did we talk about`, `note <text>`, `notes`, `clear notes`,
`list`, `say <text>`, `help`, plus fixed pleasantries (hello/hi/hey,
how are you, thanks/thank you, bye/goodbye, สวัสดี, ขอบคุณ).
One trailing `?` or `.` is ignored.
Anything else gets an honest `i do not understand`.

## Hosted resource benchmark (measured at A12, self-knowledge and grammar gaps)

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

Current numbers (A12; A11 numbers in parentheses where they differ -
A12 changed the load path, not the query paths):

| backend | facts | miss (A7) | recall (A7) | startup (A7) | peak RSS (A7) |
| --- | --- | --- | --- | --- | --- |
| interp | 0 | 2.1 ms (2.1) | - | 0.08 s | 24.1 MiB (23.6) |
| interp | 1,000 | 4.2 ms (4.9) | 0.6 ms (0.9) | 1.85 s (1.33) | 27.0 MiB (25.6) |
| interp | 10,000 | 23.0 ms (31.7) | 0.7 ms (1.0) | 16.9 s (12.4) | 57.6 MiB (46.9) |
| ir-x64 | 0 | 0.02 ms | <0.01 ms | <0.01 s | 27.3 MiB (25.7) |
| ir-x64 | 1,000 | 0.04 ms (0.02) | 0.03 ms (<0.01) | 0.06 s (0.04) | 27.3 MiB (25.7) |
| ir-x64 | 10,000 | <0.01 ms | <0.01 ms (0.09) | 0.88 s (0.67) | 177.4 MiB (124.1) |

4 GiB probe (RLIMIT_AS on the child, 10k facts, mixed recall/miss
session): both backends complete - interp 17.2 s at 57.6 MiB peak,
native 0.88 s at 177.7 MiB peak. Memory stays far inside a 4 GiB
budget.

Honest readings:
- A12's interp load increase is a ONE-TIME migration cost, not steady
  state. A pre-v5 store re-derives relation edges on first load, and
  A12 adds a bare is-a edge for every value that matches no other
  shape (all 10k synthesized values do), each with a full lowering:
  16.9 s interp cold startup vs A11's 12.4 s. Once re-saved as v5 the
  edges are persisted and the same 10k store loads in 12.2 s - A11
  speed. Native rose less (0.67 -> 0.88 s) because the compiled
  backend derives fast; its peak RSS grew 124 -> 177 MiB because those
  ~10k extra edges now persist in memory (interp +11 MiB). The cost is
  real and is the price of the kind-of edges; the north-star budget
  (4 GiB) is untouched.
- Miss/recall latency numbers swing run to run on this shared box
  (the same interp 10k build measured 10.2 and 23.0 ms miss on two
  runs); treat any single latency as a band, not a point. Query paths
  were not A12's subject and moved only within that noise.
- The A6/A7 derived structures still carry the query paths: misses and
  `did you mean` checks are word-index lookups (~100x over the pre-index
  scan at 10k facts on interp), recalls use keyset membership - no
  O(number of taught facts) work on the ordinary question paths.
  Association recall (`what do you know about`) is an intentional full
  scan.
- Usage counting is real work at LOAD time, and the interpreter route
  shows it. A10 shipped it at 20.9 s interp cold startup for 10k
  facts; A11 profiled that cost and cut it to 12.4 s (A7 was 2.6 s).
  Profiling showed the price was never the counting itself (~3 s) but
  per-character string passes: lowercasing and splitting ran as two
  full string rebuilds per key and per value (~11 s), and relation
  derivation lowercased every whole value to check four ASCII
  prefixes (~4 s, a cost A9 shipped unmeasured). A11 fuses lowercase
  + split into one pass, lowers only the 4-character prefix unless a
  shape actually matches, hoists per-pair dict lookups out of the
  counting loop, and guards the glue-word compares with a length
  check. Two plausible rewrites measured SLOWER on the interp and
  were reverted rather than kept on faith: index-based while loops
  instead of for-in iteration (+5 s), and a non-ASCII guard in front
  of the Thai pattern checks (its per-character calls cost +4 s more
  than the find()s they skipped). The remaining load cost is the
  interpreter's per-character loop overhead; there is no large win
  left on this route without a runtime-level string operation.
- Native load IMPROVED with the same changes: 0.81 s -> 0.67 s cold
  startup at 10k facts, and peak RSS 140 -> 124 MiB (interp RSS is
  flat, ~47 MiB). Still far inside the 4 GiB story.
- Query paths got no slower: misses and recalls hold their A7 latency
  (the interp 10k miss measured faster than A7's, 25.5 vs 43.5 ms -
  both are word-index lookups; the usage merge is skipped when the
  asked word was never seen).
- The held-out Thai/English dialogue (42 lines: 7 recalls incl. alias
  and Thai, 4 clarifications, 2 honest misses, 1 correction, 2
  pleasantries, 2 open questions, 2 topic chains, 6 inference checks,
  2 usage-fallback checks) scores full marks on both backends at every
  stage. Small sample: a smoke check, not an accuracy study.

`tests/test_agent_bench.py` gates the dialogue check and a tiny-scale
smoke run in CI; the full run is manual.

## What it is not

It is not a language model and does not understand language. It cannot
answer anything it was not taught, cannot generalize beyond the one
inference it has (transitive closure over explicitly taught is-in/is-a
edges, shown in its replies so the reasoning is inspectable, with
open-world negatives), matching is
literal ASCII word matching plus non-ASCII substring matching,
"associations" are shared words between taught values, and its
clarifications are word-overlap guesses. The `what does X mean`
self-knowledge for its own relation words is hard-coded text, not
learned understanding, the usage learning is co-occurrence counting
over taught facts only - it cannot say how two words are related,
cannot tell synonym from antonym from mere co-mention, and small
memories make weak statistics - and an is-a object keeps the article it was
taught with (teach `a animal` and the chain says `a animal` back -
it echoes, it does not know grammar). Thai substring matches can be
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
