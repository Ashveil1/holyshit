---
id: w1-claims-contract-v1
status: DRAFT (freeze pending fixtures + oracle pass)
---
# W1 claims contract v1 - read and keep

Owner request (2026-11-27, verbatim): "ทำให้มันอ่านเอง
และเป็นความรู้ถาวรได้ไหม ไม่ต้องเรียนใหม่หรือใช้ remember".
Consult: GPT 2026-11-27 (claim layer), Claude 2026-11-27 (four
tightenings, state machine). Both folds applied. AI-authored /
not human-validated.

## 1. Three knowledge states

- READING: session-only extraction (A16). UNVERIFIED. Never saved.
- PERSISTED_CLAIM: saved permanently after a read the owner asked for.
  Used in answers WITH the source named. Never presented as plain truth.
- ACCEPTED_FACT: a claim that passed the promote gate (section 4), or
  was taught by the owner. Taught facts outrank everything.

## 2. Claim record (canonical form)

One claim = one atomic proposition. Fields, fixed serialization order:

  key            proposition subject+scope (canonical Unicode, NFC,
                 ASCII-folded case for ASCII only; Thai kept as-is)
  value          proposition object (same canonical form)
  polarity       "pos" only at W1 (neg/uncertain never persist via gate)
  source_id      adapter-assigned: "url-N" | "corpus-N" | "text-N"
  source_kind    url | corpus | text
  locator        normalized URL / lineage id / "inline"
  revision       source revision or content hash (opaque to the core,
                 adapter-computed; empty for inline text)
  span_start     integer offset into the source snapshot
  span_end       integer offset
  excerpt        the exact span text, capped at 200 chars
  status         claim | fact | conflicted | tombstoned
  review_id      empty for unpromoted claims
  review_verdict empty | APPROVE_AS_FACT (gate output, not reviewer text)
  generation_id  integer, the batch that introduced this record
  superseded_by  claim id or empty

Identity: a claim is deduplicated on (key, value, source_id,
span_start). Ids are assigned "cl-N" in canonical batch order
(source_id, then span_start, then key) - deterministic, no clock,
no random.

## 3. Persistence

Claims live in the agent store next to facts: new state keys
"claims" (dict by id), "claim_dedup" ((key,value,source_id,span) -> id),
"claim_order", "generations" (promotion batches), "gen_next".
store.save's whitelist is extended to exactly these keys; the store
roundtrip and pre-v3 migration tests pin the bytes. A19.1's store
already proves generation-commit + torn-write fallback on this host.

## 4. The promote gate (one canonical pure function)

promote(store, batch, policy) -> (store', report)

- batch: list of PROMOTION_REQUEST records (claim fields + review_id +
  review_verdict + policy_version + generation_id). Reviewer verdicts
  are INPUTS. The core never calls a reviewer, a clock, the filesystem
  or the network.
- policy: rule table as data (below), versioned; the Oracle and every
  route load the same table.
- Processing order: canonical (source_id, span_start, key). The report
  lists one verdict per request in input order.
- All-or-nothing: if any request would exceed the storage ceiling K
  (counting records, indexes, tombstones and rollback reserve), the
  WHOLE batch commits nothing and the report says CAP_EXCEEDED.

Hard checks in order, first failure wins:
  1. SPAN      excerpt length <= 200 and span_end > span_start >= 0
  2. SOURCE    source_id exists in the store's source registry and the
               source kind is permitted by policy
  3. SCHEMA    key/value non-empty, value <= 100 chars, closed charset
  4. PRIVACY   key/value match no PII pattern (phone, email, id digits)
  5. POLARITY  polarity == "pos"
  6. REVIEW    review_verdict == APPROVE_AS_FACT, OR policy auto-pass:
               the same (key,value) already has a claim from an
               INDEPENDENT source (different host / page_id) - the
               two-source rule. A reviewer verdict is never
               corroboration.
  7. CONFLICT  contradiction state machine (section 5)
  8. DEDUP     identical (key,value) accepted fact: no-op, adds only a
               provenance line
  9. CAP       batch fits under K with rollback reserve

## 5. Contradiction state machine (rank: taught > multi-source > single-source)

- vs TAUGHT fact (same key, different value): reject. Record the claim
  as DISSENT on the taught fact's provenance. Owner authority wins.
- vs PROMOTED fact of equal or lower rank: keep both; mark both
  CONFLICTED; answers must say the sources disagree.
- vs PROMOTED fact of higher rank: reject, dissent recorded.
- Supersede: ONLY on owner action or same-page newer revision
  (same source_id, newer revision). Old record -> tombstoned,
  superseded_by set, provenance kept. A contradiction alone never
  supersedes.

## 6. Answering from claims

Recall falls back to claims when no fact matches: the reply names the
source ("<locator> says: <key> is <value>") and, on CONFLICTED claims,
says the sources disagree. "where did you learn <thing>" answers from
the stored snapshot fields (locator, revision, excerpt), never a
refetch. Claim answers carry the UNVERIFIED-source label until
promoted; promoted answers look like taught-fact answers plus an
optional "source: <locator>" suffix.

## 7. Byte-identity

Same canonical input bytes -> same output bytes on all 7 routes. The
Oracle implements sections 2-6 independently. Fixture set
tests/claims/fixtures-w1.json pins: happy promote, dedup no-op,
privacy reject, polarity reject, taught-wins dissent, conflicted
keep-both, higher-rank reject, same-page supersede, two-source
auto-pass, cap-exceeded abort, rollback inverse, order independence.
Rollback = inverse generation: marks exactly the generation's records
inactive, restores tombstoned ones it created, keeps records still
referenced by other active generations, preserves history.

## 8. Out of scope at W1

Live self-triggered fetch (W3), negative-polarity persistence,
reviewer integration transport (review records arrive as input files),
Thai grammatical parsing of sources.
