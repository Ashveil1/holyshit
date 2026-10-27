# Runnable experimental entry: gap assessment (2026-10-27)

The requested learned, assistant-like conversation is not achieved. There
is no supported broad implementation proposal at this checkpoint. This is
not evidence that pretrained weights or a particular scale are necessary.

## What actually runs

hsml_chat.py is one local REPL with supplied Thai templates, dictionary
segmentation, a labeled-bootstrap intent mapper and gold-supervised slot
extractors. Confirmed examples update mapper counts, store facts and can
propose literal shape reuse. Assertions, questions and definitions use
engineered guards. These pieces are not general language acquisition.

Original end-to-end check remains FAIL, 12/13 audit booleans true. The
remaining failure is deliberate conservative blocking of a lossy definition
that previously removed น่ะ. Actual cat-tail unknown and lotus-petal HAS
answer expectations now pass, without changing the expected strings.
Do not present this as a passing complete application.

Repeated read queries re-evaluate current facts, not stale answer strings.
Interpretation records default to128 entries, configurable0..4096 with
HSML_QUERY_CACHE_CAP. Refreshing an entry moves it to the newest position;
evict the oldest remaining entry. This is recency-order eviction, not
strict insertion FIFO. Eviction can require a new clarification/confirmation.
It does not bound the fact store, mapper, lexicon, general seen-set or
subject history. The synthetic2000-query test supplies parsed intents;
it is memory/retention verification, not2000 successful natural conversations.

Snapshots use schema_version1 and a parse-cache ABI. Legacy unversioned or
malformed records are rejected explicitly, before replacing current state.
No automatic historical conversion is implemented. Real save/load of current
entry is checked. Validation is structural and relation-compatible, not a
signature/authenticity or arbitrary untrusted-file safety guarantee.

## Remaining capability gaps

- No broad language, open-ended explanation, commonsense or discourse model.
- Supplied family mapping constrains familiar relation anchors; unmarked
  hidden intent, quotation/hypothesis and synonyms remain unresolved broadly.
- Most complex interpretation requires teacher help, precise syntax or
  clarification; code labels and scripted correctness do not prove user
  understanding of the proposal.
- B613 and B614 nested-meaning learners have substantive denotation NULLs;
  neither supports compositional-transfer integration. Equivalent syntax
  alone is not an error cause, and causes of those failures remain confounded.
- Thai tests are authored development checks, not independent evaluation;
  bilingual shared knowledge/teach-once conversation is not demonstrated.
- Snapshot compatibility is now explicit, but older files need conversion
  outside this implementation. Current version validation is not a general
  semantic-migration proof. Other growing session structures remain uncapped.

## Measurements and decision

Final B620 long-session/restart workload: sampled aggregate concurrent RSS
68,780,032 bytes. Current original entry/restart workload:68,841,472 bytes.
Supervisor and live descendants included, enforced1e9-byte cap,10ms target
sampling. These are bounded workload results, not a lifetime memory guarantee.

Concrete cache/snapshot correction is complete within the tested scope.
Do not add hand-tuned scenarios to claim progress toward the whole goal.
Further broad capability work needs a distinct hypothesis and useful
learning signal whose teacher burden is explicit. No such supported next
build is established by the current results. Preserve this internal blocker,
known failure and nulls rather than silently marking completion.
