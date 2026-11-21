# agent — a small local agent written in pure holyshit

A from-scratch local agent core for the holyshit OS direction. It runs
entirely offline inside the hs runtime: no network, no external model,
no dependencies beyond the language itself.

## What it is today (v0.2)

- An ordered pattern-rule matcher: a fixed set of command patterns is
  checked in order and the first match wins.
- A teachable memory: key/value facts it is explicitly taught, kept in a
  plain JSON-serializable Dict (`agent/core.holy`), with hosted file
  persistence (`agent/store.holy`) and a terminal chat loop
  (`agent/repl.holy`).
- A little dialogue context: it tracks the current topic (the last thing
  taught or asked about) and follows `what about it` / `forget it`, and
  it keeps short-term session `notes` that are never saved to disk.
- Association recall: `what do you know about X` answers with the taught
  fact plus other taught facts whose words overlap it (ASCII word match,
  glue words excluded) - string overlap, not understanding.
- Pure and portable: the core never does IO. `respond(state, line)`
  returns a reply, so the same core can later run freestanding in the
  kernel. Memory footprint is a few KB plus exactly what it was taught.

Commands: `remember <thing> is <fact>`, `what is <thing>` (aliases:
`do you know`, `tell me about`, `who is`, `where is`),
`what do you know about <thing>`, `what about it`, `forget <thing>`,
`forget it`, `note <text>`, `notes`, `clear notes`, `list`, `say <text>`,
`help`. One trailing `?` or `.` is ignored. Anything else gets an honest
`i do not understand`.

## What it is not

It is not a language model and does not understand language. It cannot
answer anything it was not taught, cannot generalize, matching is
literal ASCII text matching, and "associations" are shared words between
taught values, nothing more. No reply should ever be read as more than
pattern matching over taught facts.

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
