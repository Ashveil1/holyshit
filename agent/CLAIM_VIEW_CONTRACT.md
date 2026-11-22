# Claim view contract (A24.0a, FROZEN for the A24.0b re-review)

Contract id `claimview-0a`, caps version 1. Status: SPEC ONLY. No Holy code, no reply route, no Oracle and no persistence change exists for the claim view. The Python reference model (`tests/claimview/ref_claim_view.py`) and the shared fixtures (`tests/claimview/fixtures-0a.json`) pin the contract; the model passing proves nothing about a later implementation. Anything not written here is not promised.

## 1. What a claim view is
A read-only, deterministic view over current memory that answers one question about one full proposition (subject, predicate, object, polarity): what trusted support and opposition does memory hold for it, and what unverified readings mention it. It never writes, promotes, resolves a contradiction, changes a guard or pattern, or persists anything. It never reads the A12 tombstone list or the session log.

## 2. What memory holds (provenance limits)
Facts are stored as key and value strings. The original wording, the time, the teacher's identity and any correction history are NOT retained. So a view can say only what is stored now. It cannot say who said it, when, or in what words. Wording used in every view:
- assertion provenance: "stored fact in current memory; original wording and time are not retained"
- derived items: "derived by rule from stored facts; premises are not independent corroboration"
- identity: "not independently authenticated"
- quality: "evidence quality not assessed"
- readings: "unverified reading, not used for the answer"
- unknown: "no matching trusted support in current view"
These three fields (assertion, identity, quality) are separate and are never merged with the status. "Supported" is never "true". USER_CONFIRMED / USER_DISPUTED on a reading are shown as markers, not as authentication.
A stored fact's text in a view is a deterministic reconstruction from the stored tuple through a fixed phrase table (is / is not, has / does not have, is in / is not in; other predicates print as "S [not-]P O"). It is not the user's original sentence.

## 3. Canonicalization and resolution
- Canonical form: collapse ASCII whitespace runs (space, tab, newline, carriage return) to one space, trim, lowercase ASCII letters only. No Unicode normalization (NFC and NFD forms differ and do not match), no non-ASCII case folding, no stemming, no punctuation stripping.
- A subject resolves by exact canonical match with a stored key, or exact match with a taught alias whose target key exists. One distinct target key: UNIQUE. More than one: AMBIGUOUS (subject). None: NONE. Dangling aliases are ignored. Readings never resolve a subject.
- No near matches, no "seems related" hints, no fuzzy lookup. No pronouns or context: a subject or object that is a reference word (it, this, that, he, she, they, them, those, these, one, him, her) is REFUSED with a request to restate the full proposition.
- The object matches by canonical equality. A subject-only query is not part of this contract (deferred).
- An ambiguous proposition (the text fits more than one parsed proposition) is reported as AMBIGUOUS (proposition) with a capped, sorted candidate list. Parsing itself is A24.1.

## 4. Status truth table
Let P be trusted positive support (a stored edge for the proposition, or a successful derivation), N trusted opposition (a stored edge for the opposite polarity, or a successful derivation of it). Readings and blocked derivations are never in P or N.

| resolution | P | N | epistemic | basis |
|---|---|---|---|---|
| NONE | - | - | UNKNOWN | no_trusted_evidence |
| AMBIGUOUS | - | - | AMBIGUOUS | ambiguous_subject (no evidence shown) |
| proposition ambiguous | - | - | AMBIGUOUS | ambiguous_proposition (candidates only) |
| UNIQUE | yes (a stored edge among them) | no | SUPPORTED | support_only |
| UNIQUE | yes (derivations only) | no | SUPPORTED | derived_only |
| UNIQUE | no | yes | CONTRADICTED | opposition_only |
| UNIQUE | yes | yes | CONTRADICTED | both_sides |
| UNIQUE | no | no | UNKNOWN | no_trusted_evidence |

UNKNOWN means only "no matching trusted support in current view". It does not mean false, never seen or never said. Derived support depends on its premises: it is not independent corroboration, and it is never counted as more than one line of reasoning per premise chain. Readings never affect status, authenticate anything, or count as independent origins. A blocked derivation (a domain-guard stop) is shown as a note and is not evidence.

## 5. Contradiction (narrow)
Same subject, predicate and object with opposite polarity only (kind-of vs not-kind-of, has vs does-not-have, verb vs not-verb). Different objects of the same predicate are not a contradiction. Conflicts on functional predicates wait for the A22.1 registry and are out of scope. Both sides are shown with their evidence. No winner is chosen by recency, count or source.

## 6. Pipeline, privacy and failure rules
Fixed order: resolve target -> eligibility/privacy -> order -> cap -> render. Never render then hide.
- The repl supplies an exclusion input `{"version": 1, "sources": ["id", ...]}`. Core does no I/O.
- Eligibility removes excluded reading entries before ordering, counting, capping and display. A reading record with no eligible entry vanishes.
- Excluded readings are fully silent: no "N hidden", no count, no placeholder. The output must equal the output for a state in which those readings do not exist.
- FAIL CLOSED: a missing or malformed exclusion input (anything except the exact shape above, including a wrong version, a non-list, or a non-string or empty source id) suppresses the readings section entirely. The output then equals that for a state with no readings. Status and trusted evidence are unaffected.
- Reading entries without a usable string source id are dropped.
- The same rule covers every path: UNIQUE, NONE, ambiguity and any future subject listing. Ambiguity candidates come only from taught keys and aliases, never from readings.
- Truncation counts ("N more") are computed after eligibility.
- No cache, memo, index or id is kept. Nothing is user-visible as an id or hash; any numbering in a rendering is local to that reply.

## 7. Ordering, caps, derivations
- Order inside a section is lexicographic on the reconstructed text, then rule name (readings: source id, sentence, side). It does not use insertion order or time. It is deterministic. It is NOT a reliability ranking and NOT chronology, and no rendering may say otherwise.
- Caps (versioned starting values, caps version 1): 5 support, 5 opposition, 5 readings, 5 candidates. Excess is reported explicitly as a count, never silently dropped.
- Derivation depth: the root conclusion is depth 0 and not counted; premises of the root are depth 1; their premises depth 2. Premises deeper than 2 are not expanded, and `derivation_nodes` truncation is reported explicitly when a rule might have applied deeper.
- Total derivation nodes per view are bounded (20). Hitting the bound sets the same truncation flag.
- Cycles are detected along each path: a branch that returns to a proposition already on its path is not a proof and is cut.
- Rule family modelled: X P Y if X is Z (stored) and Z P Y (provable), with guards as (predicate, kind) stops. The real core's rules are broader; mapping them is A24.0b work that needs re-review.

## 8. Deletion
Ordinary forget removes key, aliases, relations and index entries (existing behavior). The A12 tombstone (key only, last 20, persisted) and the session log remain as owner-facing features and are never read by a view. Ordinary forget is therefore NOT complete privacy erasure while keys remain in tombstones. A separate privacy-erasure operation (tombstones and session logs included) is not defined here and needs its own step. A view of a forgotten claim is UNKNOWN with no trace. There is no history of corrections to show.

## 9. Non-goals and invariants
Read-only: state and the exclusion input are not mutated. No pronouns, no references, no dialogue state (A25/A26). No numeric confidence. No ordinary-reply change: existing replies, the `why is` route and the 7-route corpus stay byte-identical. No Thai surface (pending Ash). A23 classifier c1 is untouched; a later c2 is NOT_DIRECTLY_COMPARABLE with c1 results.

## 10. Fixtures and later parity
`tests/claimview/fixtures-0a.json` (24 cases) is the shared edge-case set for the reference model now and the Oracle later. It covers: alias collision, dangling alias, ambiguity, NFC/NFD, non-ASCII case, Thai, cycles, depth truncation, guard stop, both-side evidence, derivation-only support, excluded and malformed-exclusion readings, reading-only subjects, and pronoun refusal. The contract tests also enumerate the 16-row truth table, read-only checks, order independence, cap and truncation arithmetic, and the privacy equivalences. Thai/Unicode divergence between interp and compiled backends (char vs byte, `json_str`) must be checked on the real implementation before A24.0b can claim parity.
