# HSML — dialog-taught experimental system (user guide)

**What this is:** an experimental research system you teach through Thai
conversation. It is **not** an LLM: there are no neural weights and no
pretraining. It has a small seeded skill library (derived at startup from
committed, verified logs), an attribute memory you teach facts into, and a
dialog teaching protocol that searches for a program matching your examples.
It answers exactly inside what it was taught and abstains honestly outside it.

**Status:** research code. Master is CI-validated; the latest committed work
lives on the development branch (see "Which version" below). No package, no
service, no release — you run it from source.

## Requirements

- Python 3.10+ (standard library only — nothing to pip install)
- CPU only; no GPU, no network needed at runtime

## Quickstart (tested)

```sh
git clone https://github.com/Ashveil1/holyshit.git
cd holyshit/ai/wnn
python3 chat.py --demo-world
```

`--demo-world` first teaches the built-in Thai animal demo world (219
statements, same content the test suites use), then drops you into chat.
You can run `chat.py` from any directory; paths resolve from the repo.

Type `help` inside the chat for the phrasing cheatsheet. Type `quit` to save
and exit. Your memory autosaves every turn.

## Which version

| path | what you get | validation |
|---|---|---|
| `master` branch | the CI-validated system | quick CI + recorded test suites (LEDGER.md) |
| `wnn-checkpoints` branch | latest committed work (newest fixes/features, e.g. dynamic vocabulary, retraction, reverse queries, storage-safety guards) | each change passes its own pre-registered harness and regressions (LEDGER.md), but lands on master only after its PR's CI goes green |

To run the latest committed development state:

```sh
git checkout wnn-checkpoints
python3 chat.py --demo-world
```

`LEDGER.md` in this directory records every experiment: pre-registered
criteria, failures, corrections, and verdicts. Read it before trusting any
capability claim — branch-tested does not mean master-landed.

## What you can say (exact Thai phrasings)

Phrasings are exact by design; other phrasings get an honest no-answer.
This is a finite designed interface, **not** general Thai understanding.

Teach a procedure by examples:
```
วิธีนี้ชื่อ สองเท่า          name a new way
ถ้า n เป็น 7 ตอบ 14         example (it collects 5)
ถ้า n เป็น 2 ตอบ 4
...
ตอบ 474                     answer its check questions
สองเท่า ของ 97 คืออะไร      use it  ->  สองเท่า ของ 97 คือ 194
```

Facts about things:
```
แมว มี ขน และ หาง           teach a fact
แมว มี อะไรบ้าง             what does X have?
แมว มี ปีก ไหม              yes/no: ใช่ (taught) / ไม่ (retracted) / ไม่รู้ (never taught)
แมว ไม่มี หาง               retract a fact (leaves explicit negative evidence)
ขน และ หาง                  probe: which things have these?
```

Teaching a new procedure triggers a program search. Cost is strongly
target-dependent: a simple target (doubling) is found after ~10^3 candidate
programs (sub-second here); harder targets can search for minutes of CPU and
can fail honestly (`teach_failed`) instead of guessing. Answering with
already-known skills and facts is effectively instant (measured ~0.04 s CPU,
~11 MB peak RSS for startup + 219-statement world + queries on one sandbox —
a single measurement, not a hardware guarantee).

## Memory and updates

- Everything you teach lives in one local file (default `./hsml_memory.pkl`).
- Updating the code never touches it: `git pull`, then restart `chat.py`
  with the same `--memory` path. On load, the baseline library is re-derived
  from the updated code and your saved state is overlaid on top.
- If an update changes a skill your taught skills build on, dependent skills
  are marked stale and refuse to answer until you re-confirm them — an
  intentional honesty mechanism, not data loss.
- **Safety:** a memory file is a Python pickle. NEVER load one from someone
  you do not trust — loading a pickle executes code. If you share your
  memory file, it carries everything you taught, including anything private
  you typed. There is currently no supported safe-export format for sharing
  taught state with strangers.

## Honest limits

- Narrow Thai coverage, finite designed frames; unknown phrasing = abstain.
- No general language understanding, no common sense, no knowledge beyond
  what you teach it.
- Teaching search can be expensive; there is no guarantee a target is found.
- Single-user, local, no concurrency, no access control.
