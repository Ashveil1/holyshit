# Spec v2.5: AI-authored thai-core held-out eval set (thai-core v1, AI path)

Status: DRAFT v2.5 for the GO review. Supersedes v2.4 (same file, -v2.4.md).
v2.4 got NO-GO - one substantive blocker plus two consistency fixes, core
methodology explicitly retained (26 Nov, GPT, same thread). v2.5 makes the
targeted corrections only:
B1 (preflight edge cases) -> section 4.2: EXACTLY 5 usable examples per
category after replacement or the category waits (no 3-4 denominator);
5/5 structural, 5/5 instruction, >=4/5 task match; the two preflight
reviewers named (Claude + GPT, the Phase 1 cross-review pair); reviewer
disagreement on an instruction-compliance violation = category FAILS
preflight pending a new agreed assessment - no discretionary adjudication
by main+GPT.
B2 (schema consistency) -> sections 3.4 and 9: authors.author_id used
consistently (was authors.id in 3.4).
B3 (section 9 wording) -> milestone bar now says: the SEPARATE Thai
serialization test corpus is byte-identical across the 7 routes; the
frozen thai-core scenario corpus is NOT executed in C19 parity testing.
Optional folds: shuffle seed now mixes in annotator_id (decorrelated
orders across annotators; logged order stays the evidence); stale
version-history wording in section 0 corrected.

Owner decision and non-negotiables are unchanged (Ash 26 Nov 10:44 / 10:45
UTC: he will not author; do it all; main's 10:44:34 reply set the
"AI เขียน / not human-validated / never a quality claim" labeling, which
stays a hard design constraint). Owner-reserved escalations stay delegated
to main+GPT (22 Nov 09:13 UTC): negative polarity, privacy incidents,
reviewer conflicts, FP confirmation + quarantine lift.

## 0. Verdict history

v1 BLOCKED (6 points) -> v2 -> v2.1 (Variant A committed with Gemini) ->
v2.2 NO-GO "precision, not redesign" -> v2.3 NO-GO, two blockers,
architecture and 70-item target explicitly accepted -> v2.4 NO-GO, one
substantive blocker (preflight edge cases) plus two consistency fixes,
core methodology retained. This file is v2.5; every NO-GO point is
addressed inline and cross-referenced in the header map above.

## 1. Non-negotiables (binding on every artifact)

1. "AI เขียน / AI-authored, not human-validated" on every item, report,
   baseline and status line. Structural where possible (checker-enforced),
   not editorial.
2. Results are NEVER cited as proof of quality - not to Ash, not in README,
   not in baselines. Breakage-catching only.
3. No tuning against the set, before or after freeze. No per-item results
   are inspected before content freeze; after freeze, results are reported
   at suite level. A suspected defect found via the set is reproduced with a
   NEW case outside thai-core (dev set or unit test); the fix cycle never
   iterates against thai-core items. Regression handling stays open loop
   (A23.0): a REVIEW_REQUIRED-style signal, nothing else.
4. thai-core stays a separate suite: id "thai-core", kind "thai-dataset",
   tier supported - where tier:supported declares CAPABILITY SCOPE only
   (the capability the suite exercises is a supported surface), never a
   validation or quality claim about the set or the agent (improvement E).
   The dev set keeps id "thai-dev-ai", kind "dialogue", tier challenge,
   frozen=false, its existing "not independent" note.
5. Escalations (negative polarity, privacy incidents, reviewer conflicts,
   FP confirmation + quarantine lift) route to main+GPT under the 22 Nov
   delegation.

## 2. Pipeline (order is binding)

Phase 0 - this spec approved at the design gate.
Phase 1 - CRITERIA: the criteria-first round. Claude and GPT each PROPOSE
  the seven acceptance criteria independently (same brief, no sight of each
  other), then cross-review the other family's proposal. Disposition per
  criterion (REPLACES v2's "stricter wording wins" - verdict Q3 REJECTED
  that rule: GPT is a criteria-authoring family, so main+GPT cannot
  adjudicate a dispute involving its own proposal):
  - agreement after the cross-review exchange -> the criterion freezes;
  - persistent disagreement after the exchange -> CRITERIA_UNRESOLVED,
    recorded with both wordings; the AFFECTED CATEGORY is blocked and does
    not proceed to authoring; the other resolved categories continue.
  The merged, agreed result is criteria version 1, frozen (CRITERIA
  FREEZE, hash pinned in the freeze attestation, section 6.1) before any
  item exists. N = 10 x (frozen categories), split about equally between
  Claude and GPT; Gemini annotates all N (B3). If any category is
  blocked, the pilot is smaller than 70 and says so.
Phase 2 - VARIATION PLAN: per category, the intended variation is written
  down before generation: registers (plain spoken, polite particles),
  sentence shapes, entity types, negation forms, pronoun usage, scenario
  lengths. The variation plan is HASH-PINNED (improvement C) in the freeze
  attestation. 10 scenarios per category x (frozen categories) = N items; a
  scenario (setup + probes) counts as 1 item.
Phase 3 - AUTHORING: split across two families per section 4. Authors see
  ONLY: the frozen criteria, the variation plan, the capability-level
  description (no code, no outputs, no dev-set items, no failure modes).
Phase 4 - ANNOTATION: blind, variant A (section 4), after the Gemini
  preflight (section 4.2). Batched and quota-aware (section 4.5); every
  annotation produces a decision record (section 4.6).
Phase 5 - RESOLUTION: agreement -> scored; disagreement -> unresolved pool
  (section 4.4). No self-adjudication. Critical/ambiguous items never
  become scored on the AI path (section 4.4).
Phase 6 - GATES: checker clean + overlap gate clean + report committed +
  freeze attestation (section 6.1) -> CONTENT FREEZE (section 7). C19
  parity -> EXECUTION ELIGIBILITY recorded OUTSIDE the frozen content
  (section 7) -> baseline capture with pinned examinee build hash.
Phase 7 - OPERATION: report-only milestone runs under the section 8 rules.

## 3. Format changes vs A23.3 / T-SE16 (checker impact)

### 3.1 Provenance (improvement B + verdict B4: identity vs session)

provenance.method gains "ai-authored". Requires:
- authors: list of {author_id, family, model, version, session_date} -
  author_id is a STABLE project-generated identity ("claude-author-01",
  "gpt-author-01"), family one of "claude" | "gpt" | "gemini" (mandatory
  for authors as well as annotators, verdict section 4).
- annotators: list of {annotator_id, family, model, version} - STABLE
  identities only, exactly ONE entry per annotating identity; version is
  "unavailable" verbatim when the service exposes none (section 4.1).
- annotation_sessions: list of {session_id, annotator_id, session_date,
  batch_id, resume_of, displayed_model_label, prompt_template_hash,
  item_order_seed} - one entry per ACTUAL conversation/session; an
  annotator works across many sessions, sessions never share an id, and
  resume_of chains a resumed session to its predecessor (or null).
  Annotation records reference BOTH the session and (through it) the
  stable annotator identity, so the family-level check in 3.4 is
  deterministic and no identity record is ever duplicated (B4).
- criteria_version, variation_plan_hash.
- "human_validated": false as a mandatory literal - missing or true
  refuses the suite.

### 3.2 Statuses (suite) - execution field REMOVED from frozen content

Statuses: "AI_AUTHORED_DRAFT" -> "AI_AUTHORED_REVIEW" ->
"AI_AUTHORED_CONTENT_FROZEN". The v2.1 "execution" field inside the suite
file is REMOVED (verdict Q4 + section 3.2 contradiction): execution
eligibility is an EXTERNAL record (section 7.3) that references the frozen
suite hash, so the frozen file never changes when C19 lands. The
owner-authored statuses stay valid (future human set).

### 3.3 Item states: progress x disposition (structural, verdict 2C)

Two orthogonal axes, both checker-enforced:
- annotation_progress: "pending" -> "partial" -> "complete". "partial"
  means exactly one of the two required annotations exists. An item may
  become scored ONLY from complete.
- disposition: "scored" | "unresolved" (set only when complete).
  Unresolved items carry "unresolved_reason" (one of
  "annotator-disagreement" | "no-independent-adjudicator"), stay in the
  file, and are excluded from the scored counts; thai-check reports them
  separately. The old adjudication states stay for the owner-authored
  path.

### 3.4 Per-item provenance (checker-enforced, FAMILY-LEVEL)

Every item carries "authored_by" (an authors.author_id), "ai_authored": true,
"not_human_validated": true (both mandatory literals), and
"annotation_ids" (annotation records in the annotation log, section 4.6).
The checker enforces, at FAMILY level (not string comparison - verdict
section 4):
  author.family of the item NOT IN {annotator families of that item}
A Claude author and a different Claude session are the same family and
MUST fail this invariant. Identity strings alone are not evidence of
independence.

### 3.5 Three artifacts, not one suite file (verdict B1)

v2.2's "thai-dataset not a runnable suite (ids/counts only)" contradicted
section 7's "the frozen suite is run". Resolved by splitting the artifact:
- thai-core MANIFEST: dataset identity, metadata, provenance, statuses,
  item ids and counts, item states, per-item provenance. The checker view
  (A23.3/T-SE16 semantics) operates on the manifest: ids/counts only,
  never executed.
- thai-core SCENARIO CORPUS: the actual Thai content - setup lines,
  dialogue, probes, expected labels - referenced from the manifest by
  item id. Frozen with the manifest.
- thai-core EVALUATION HARNESS: a separate, versioned component that
  CONSUMES the scenario corpus and invokes the agent's execution routes
  (repl subprocess per scenario). The harness is code, not corpus; it is
  pinned by IMMUTABLE SOURCE/BUILD HASH (v2.4) wherever results are
  reported.
The freeze attestation pins manifest hash + corpus hash + harness
source/build hash (section 6.1). "Running the frozen suite" (section 7)
means: the pinned harness build consumes the pinned corpus.
Item rules unchanged otherwise: origin=authored (native Thai, never
translated or scraped), category semantics.

### 3.6 Suite note

The one-line honesty position (v1 wording, kept).

## 4. Annotation design - VARIANT A COMMITTED (three families)

- Allocation is DERIVED, not fixed (verdict B3): N = 10 x (number of
  categories with frozen criteria). Claude and GPT receive approximately
  equal authoring allocations totalling N (differ by at most 1); Gemini
  annotates all N eligible scenarios. The 35/35/70 numbers apply only
  when all seven categories are frozen; a blocked category reduces N and
  the pilot says so.
- Claude-authored items: annotated by GPT + Gemini. GPT-authored items:
  annotated by Claude + Gemini. Every item gets two annotations,
  family-distinct, neither from the author family; the checker enforces
  the family-level invariant (section 3.4).
- Gemini annotates all N items, Claude and GPT about N/2 each. Gemini's
  systematic bias can therefore touch every pair: disagreement rates are
  reported PER PAIR (GPT+Gemini, Claude+Gemini) AND PER CATEGORY, never
  only as one aggregate number (verdict 2A).

### 4.1 Provenance honesty (verdict 2A)

Record per session: service ("gemini.google.com"), access tier
("free"), displayed model label as shown at session time, session date,
and the project-generated session id. NEVER invent a version identifier;
NEVER assume the same underlying model across sessions. Account labels,
emails and other personal account identifiers are NOT recorded in
committed provenance (verdict 2E).

### 4.2 Gemini preflight gate (verdict B5: acceptance defined up front,
v2.4: deterministic pass/fail rules pinned BEFORE the run)

Before any corpus annotation: Gemini annotates a separate set of
NON-CORPUS Thai examples (namespace "gemini-preflight-", never entering
thai-core). The acceptance criteria are DEFINED BEFORE THE RUN, in three
dimensions, each scored per category type:
1. STRUCTURAL COMPLIANCE: correct output format, all required fields
   present, no missing decisions.
2. INSTRUCTION COMPLIANCE: follows the annotation instructions, invents
   no missing facts.
3. CATEGORY TASK PERFORMANCE: produces the predefined expected annotation
   on the predefined non-corpus examples for that category type.

Deterministic pass/fail rules (pinned here, before any preflight run;
changing any of them requires a new spec revision BEFORE the run):
- EXAMPLE COUNT: EXACTLY 5 USABLE preflight examples per category AFTER
  the replacement step below (7 categories -> 35 non-corpus examples when
  all categories are frozen). If a category cannot reach exactly 5 usable
  examples, its preflight DOES NOT RUN and the category WAITS - Gemini
  cannot annotate it. There is no 3-or-4-example path: the denominator
  is always 5 (v2.5, verdict B1). Each example is scored on all three
  dimensions.
- STRUCTURAL COMPLIANCE: must be 5/5 per category. One structurally
  non-compliant response (unparseable output, missing field, missing
  decision) fails the category. No tolerance.
- INSTRUCTION COMPLIANCE: must be 5/5 per category. One invented fact
  (any content in the annotation not derivable from the example text and
  the instructions) fails the example AND the category. No tolerance.
- CATEGORY TASK PERFORMANCE: pass threshold is AT LEAST 4 OF 5 examples
  per category with a MATCHING expected annotation. The mismatched
  example and the raw output are recorded in the session log either way.
- PERMITTED EQUIVALENCES: the decision/label field comes from a CLOSED
  ENUM frozen with the criteria. A response matches only if it emits the
  exact enum token after normalization (Unicode NFC, whitespace folding,
  case folding) or a token listed in a FROZEN EQUIVALENCE TABLE (a short
  explicit mapping, e.g. Thai/English spellings of the same enum value,
  pinned in the preflight plan before the run). Rationale text is
  free-form and NEVER scored. Any other formulation counts as a mismatch -
  there is no reviewer judgment call at scoring time.
- AMBIGUOUS PREFLIGHT ITEMS: the preflight examples and expected
  annotations are prepared by Claude and GPT independently and
  cross-reviewed under the Phase 1 dispute rules. Any example whose
  expected annotation the two families cannot agree on is REMOVED and
  REPLACED before the run; it is never adjudicated during or after the
  run. Replacement continues until the category has exactly 5 usable
  examples or the category waits (rule above).
- THE TWO PREFLIGHT REVIEWERS (named, v2.5 verdict B1): the Claude and
  GPT authoring families - the same cross-review pair as Phase 1. Each
  scores the preflight independently from the recorded raw outputs.
- REVIEWER DISAGREEMENT: if the two reviewers disagree on whether an
  example violates instruction compliance (or on any other scoring
  call), the category FAILS the preflight pending a NEW, AGREED
  assessment - a failed-pending category waits like any failed category.
  There is NO discretionary adjudication by main+GPT or anyone else: an
  ambiguous scoring decision can never silently become a pass.
- CATEGORY-LEVEL OUTCOME: a category passes iff all three dimension rules
  above pass under BOTH reviewers. The outcome is computable from the
  recorded raw outputs by the two reviewers reaching the SAME result -
  that reproducibility is the point of this gate.
The preflight itself is labeled AI-authored / not human-validated, and a
PASSED preflight is structural process evidence only - it is never cited
as evidence of Thai semantic reliability. A FAILED category blocks
Gemini's annotation of that category: under variant A the category then
WAITS (like a quota wall) - it is never silently re-annotated under
another arrangement. Results (pass/fail per category type per dimension,
the per-example scoring, and the raw outputs) are recorded in the session
log.

### 4.4 Disagreements and critical/ambiguous disposition (verdict: explicit)

- Annotators agree AND the item is not critical/ambiguous -> scored.
- Annotators disagree (any category, any criticality) -> unresolved pool,
  "annotator-disagreement".
- CRITICAL or AMBIGUOUS items on the AI path: the inherited checker rules
  require adjudication, and no independent adjudicator exists on this
  path, so these items go to the unresolved pool with reason
  "no-independent-adjudicator" EVEN WHEN BOTH ANNOTATORS AGREE. This is
  stated explicitly here so it is never implicit (verdict section 4).
  Authors are told in the brief that critical/ambiguous flags consign an
  item to the unresolved pool on the AI path.
- No item is "adjudicated" unless a genuinely independent adjudicator
  exists (a human, or a future party outside the annotating families AND
  outside the author family of that item). Today none exists.
- main+GPT may review process and safety (wording severity, privacy,
  polarity) but a dispute involving their own family is never described
  as "independently adjudicated" - the phrase is banned from reports.
- The unresolved pool is not a challenge tier. Deliberate challenge probes
  are deferred to a future suite version.

### 4.5 Batching, sessions, quota (verdict 2B/2C/2D)

Identifiers, now SEPARATED:
- batch_id: stable identity of a planned group of items (max 10, one
  category per batch).
- session_id: one actual conversation/session with a model.
- annotation_id: one item's annotation record.
- resume_of: optional reference from a session to the previous session.
A batch MAY span multiple session_ids when a quota interruption forces a
new session; a session never spans batches. A MODEL-SELECTION CHANGE (or
any account change) always starts a new session_id and is recorded;
switching silently is banned.

Batch size: at most 10 items AND at most a pinned MAX BATCH PAYLOAD:
24 KiB counted as the UTF-8 bytes of the exact serialized prompt body
sent to the model (template wrapper + item texts), excluding transport
framing. "Exact client-submitted prompt text" means the text under the
PROJECT's control and inspection; hidden provider-side system
instructions or internal wrappers that cannot be inspected through the
Gemini web interface are outside the definition by construction
(verdict, 24 KiB clarification). Exceeding the cap splits the batch.
Item order within a batch is RANDOMIZED with the algorithm pinned
(initial: Python random.Random(seed) shuffle, seed = sha256 of
batch_id + ":" + annotator_id, truncated to 8 bytes, big-endian -
annotator_id is mixed in so the two annotators of one batch do NOT
receive the same item order, v2.5 optional fold; the PYTHON RUNTIME
VERSION used is recorded per session) to limit cross-item context
effects; the exact prompt template is hashed per session
(prompt_template_hash).
Reproducibility belt-and-braces (verdict): the ACTUAL ORDERED ITEM-ID
LIST of every batch as presented to the model is recorded in the session
log, so the presentation order is directly reproducible from the log even
if the PRNG or runtime later changes; the algorithm pin remains the
statement of intent, the logged order is the evidence.

Quota rules: pause on an ACTUAL quota-limit notification; record the
displayed reset information verbatim if shown; resume only when capacity
is available; do NOT assume a daily reset; do NOT switch model or
account to work around a wall. There is no deadline; throughput follows
the quota.

Partial progress is structural (section 3.3): the checker accepts a
suite at AI_AUTHORED_REVIEW with pending/partial items and refuses
CONTENT FREEZE until every item is complete with a recorded disposition
(improvement D wording: "all items have a recorded disposition", never
"all items resolved").

Blindness is preserved under batching: a session sees only its batch's
items, the frozen criteria and the frozen criteria version - never the
author's intent, the other annotator's labels, or agent outputs. One
session at a time on the Gemini account (single browser profile).

### 4.6 Annotation decision records (improvement A + verdict B2)

Every annotation is a record: {annotation_id, item_id, batch_id,
session_id, annotator_id, criteria_version, prompt_template_hash,
timestamp, label, rationale, response_hash} where response_hash is the
hash of the ORIGINAL structured model response (the immutable
annotation-output artifact - this matters most for Gemini, whose exact
model version is unavailable). The ORIGINAL RAW MODEL RESPONSES are
RETAINED as committed evidence files alongside the annotation log (one
file per session, hash-pinned), so every response_hash is independently
re-verifiable from the retained artifact, not just asserted (verdict B2
qualification). Records are append-only, committed with the suite as
evidence, and hash-pinned in the freeze attestation (6.1).

### Variant B - contingency only, separately gated (verdict 2F + Q1)

Default on any Gemini unavailability: PAUSE AND WAIT (Q1). Variant B
activates ONLY if Gemini is PERMANENTLY unavailable, and then only via a
SEPARATE approval and freeze decision - never automatically on a quota
wall. Rules if it ever activates:
- annotation_variant: "B" in the suite provenance; every report says
  "single-independent-annotator"; no claim of two-annotator agreement.
- Each item gets ONE independent annotation from the non-author family;
  the author family records a self-review with role "author-self"
  (declared NOT independent, never counts toward agreement; a
  self/independent clash sends the item to the unresolved pool).
- NEVER mix Variant A and Variant B items into one undifferentiated
  scored population: variant B is a separately versioned corpus or a
  separately frozen annotation realization with its own provenance and
  reporting. Partially completed variant A work is NOT completed by
  author-self concurrence.

## 5. Overlap gate (screening, not independence) - verdict Q2 safeguards

Wording: "separate AI-authored set, screened for overlap with
thai-dev-ai-v1". The gate:
1. Unit of comparison: the WHOLE scenario unit AND every individual
   setup/dialogue/probe line (both, verdict Q2).
2. Methods (all deterministic; the overlap report PINS its own inputs,
   verdict B2: thai-dev-ai-v1 content hash, overlap checker
   implementation/build hash, Thai tokenizer + dictionary/model hash,
   normalization configuration, sequence-similarity algorithm +
   parameters, minimum meaningful text length, threshold configuration -
   so the report alone proves WHICH dev-set version and tooling compared
   what):
   - exact normalized match (Unicode NFC, whitespace/case folding):
     automatic rejection;
   - token-set Jaccard >= 0.80: flag for review; >= 0.95: automatic
     rejection only when the text is above a minimum meaningful length
     (recorded in the report);
   - a SEQUENCE-AWARE similarity (pinned algorithm + version) alongside
     token-set Jaccard - token sets lose word order, misleading for
     short Thai phrases;
   - containment check for items under 5 tokens: flag for review, never
     automatic rejection.
   Changing thresholds, tokenizer or algorithms is a re-screen.
3. Scenario-id namespaces disjoint ("tc-" vs dev "d-"/"s-").
   Thresholds are OPERATIONAL, not proven semantic-duplicate detection -
   the report says so.
4. Output: a committed overlap report - every match, every borderline
   pair with its score, the decision per pair (rejected / rewritten /
   kept-with-reason), checker + tokenizer versions. The report is
   evidence, hash-pinned in the freeze attestation (6.1).

## 6. Immutability, exclusion ledger, and FP-independence (blocker 3)

- After CONTENT FREEZE the suite content never changes. No removal, no
  in-place edit.
- EXCLUSIONS ARE OBJECTIVE ONLY (improvement F): an exclusion requires an
  objective defect (broken scenario, wrong category, duplicate, malformed
  label) - a SEMANTIC dispute about the right label is never an exclusion;
  it goes to the unresolved pool ("annotator-disagreement"). Exclusions
  must never become an agent-debugging channel: a suspected agent defect
  is reproduced OUTSIDE thai-core (section 1.3), and that is the only
  allowed use.
- FP confirmation flow (delegated to main+GPT, 22 Nov): the confirming
  reviewer's family is recorded in the ledger entry, and the entry is
  labeled "confirmed under delegated owner authority - reviewer NOT
  independent of the annotating families" (independence is disclosed,
  not faked; the delegation supplies the authority, the ledger supplies
  the honesty). HARD RULE (verdict): delegated FP confirmation or
  quarantine lifting can NEVER convert a semantic disagreement into an
  objective exclusion - semantic uncertainty stays in the unresolved
  pool, and a ledger entry whose defect class is contested is refused by
  the checker. QUALIFICATION (v2.4, verdict section 4): "wrong category"
  counts as an objective exclusion ONLY when it is demonstrably
  established against the FROZEN CATEGORY CRITERIA (the evidence
  reference in the ledger entry must show the frozen criterion text the
  item violates); a contested semantic classification is never an
  exclusion and stays unresolved.
- Ledger entries: {item id, objective defect class, evidence reference,
  reviewer identity + family, disclosure label, date, prev_entry_hash}.
  Append-only with INTEGRITY PROTECTION (verdict B2): each entry chains
  to its predecessor's hash (genesis entry chains to the manifest content
  hash), the checker validates the whole chain, and every report cites
  the head hash.
- Every report cites: suite content hash, ledger hash, active count
  (scored minus excluded). Any content change = new suite version, full
  re-freeze including the overlap gate.

### 6.1 Freeze attestation (blocker 5 + verdict B2)

CONTENT FREEZE produces a freeze attestation file pinning the hashes of:
manifest content, scenario corpus, exclusion ledger head, variation plan,
criteria v1, session log, annotation decision log, raw-response evidence
files, overlap report, prompt templates, and the evaluation harness
identity - pinned as an IMMUTABLE SOURCE/BUILD HASH (content hash of the
harness source tree, or its release/build digest when one exists), never
only a human-readable version string (verdict B2 qualification). The
attestation is ANCHORED immutably: it is committed to the holyshit repo
and the containing GIT COMMIT HASH is recorded as its anchor (a signed
release record can replace this when one exists) - the attestation is
never the unpinned authority for the other pins. ARTIFACT ROLES (v2.4,
verdict B1 terminology fix): the MANIFEST is the checker-facing metadata
and provenance; the SCENARIO CORPUS is the actual evaluation content;
MANIFEST + CORPUS JOINTLY constitute the frozen evaluation dataset; the
HARNESS executes that dataset. Neither artifact alone is "the dataset" -
and the attestation makes the EVIDENCE of how the dataset was produced
tamper-evident too.

## 7. Three gates, split (blocker 4 resolved per Q4)

1. CRITERIA FREEZE (Phase 1): criteria v1 hash pinned (or
   CRITERIA_UNRESOLVED for blocked categories). No items exist yet.
2. CONTENT FREEZE (Phase 6): every item complete with a recorded
   disposition (scored or unresolved pool), checker clean, overlap gate
   clean with committed report, freeze attestation written, statuses
   flipped, content hash pinned. Does NOT require C19. The real Thai
   scenario corpus is authored, committed, hashed and frozen as a UTF-8
   data artifact at this gate, independent of C19 - C19 gates EXECUTION
   only, never authoring or content freezing (v2.4, verdict B1). Nothing
   about the agent has been run.
3. EXECUTION ELIGIBILITY: an EXTERNAL eligibility record (never a field in
   the frozen artifacts), referencing: frozen manifest + corpus hashes,
   the C19 implementation/build identity, seven-route parity evidence,
   evaluation harness source/build hash, test versions, the eligibility
   decision and its date. The C19 route-parity proof runs a SEPARATE
   THAI SERIALIZATION TEST CORPUS (purpose-built serialization fixtures),
   NEVER thai-core itself - parity testing must not execute the frozen
   set (verdict B1). Until the eligibility record exists the set is never
   run, and the frozen artifacts never change when C19 becomes fixed.
   Baseline capture happens only after eligibility: the pinned harness
   build consumes the frozen scenario corpus once against the
   then-current agent build, the EXAMINEE BUILD HASH is pinned with the
   baseline (replies-vXXX.json pattern extended with a build field), and
   the baseline is labeled AI-authored + not human-validated. Content
   freeze first, baseline later; no per-item results exist before
   content freeze, ever.

## 8. Usage, reporting, pipeline health

- Report-only milestone runs once eligible. Every number carries "AI เขียน
  / not human-validated". Phrased to Ash as breakage-catching only.
- Suite-level reporting only (per-category and total); per-item results
  are not reported and not inspected for fixing (section 1.3).
- Pipeline health is measured and reported instead of agent quality:
  authoring throughput, annotator disagreement rate PER PAIR AND PER
  CATEGORY (section 4), unresolved-pool size and reason split,
  overlap-gate hit/borderline counts, exclusion-ledger growth, quota
  interruptions. These say how much the SET can be trusted as a breakage
  instrument, never how good the agent is.
- Optional owner spot-check stays open and unforced (5 items whenever);
  recorded as role "owner-review" annotations, additive only, never flips
  human_validated.

## 9. Implementation impact (when approved; separate gated step)

- agent/selfeval.holy thai-check: manifest/corpus split (checker reads
  the manifest; corpus referenced by hash); provenance enum + mandatory
  human_validated:false; stable author/annotator identities with family +
  separate session records; family-level author/annotator exclusion;
  progress x disposition item states; statuses without an execution
  field; variant A/B rules (variant recorded); annotation-log (with
  response_hash), session-log, overlap-report (input pins) and freeze-
  attestation validation (incl. git-commit anchor recording); exclusion
  ledger hash-chain validation (objective classes only; contested defect
  class refused).
- tests/test_agent_selfeval_thai.py: extended for all of the above
  (refusal cases: same-family annotator via DIFFERENT session ids,
  missing human_validated, scoring a partial item, disagreement ->
  unresolved, critical/ambiguous -> no-independent-adjudicator even on
  agreement, ledger append-only + chain tamper detection, attestation
  hash coverage, duplicate annotator identity refused, preflight
  evidence shape).
- tests/selfeval/thai-core-v1.pending.json: template gains the manifest
  shape; the scenario corpus is a SEPARATE UTF-8 DATA ARTIFACT that is
  authored, hashed and frozen before C19 (C19 gates execution only,
  never corpus authoring or freezing - v2.4, verdict B1); the evaluation
  harness is a new versioned component, pinned by immutable source/build
  hash (harness identity pinned in the freeze attestation and the
  eligibility record).
- agent/README.md: PENDING-owner-labeling text replaced by the AI-authored
  path, three-gate description with the external eligibility record,
  honest wording.
- Milestone bar at implementation: the SEPARATE Thai serialization test
  corpus (purpose-built serialization fixtures) is byte-identical across
  all seven execution routes; the frozen thai-core scenario corpus is NOT
  executed as part of C19 parity testing (v2.5, verdict B3 wording). Eval
  zero-FP, Oracle mirror if core changes (none planned), deterministic
  scenarios + isolation gates, bench, honest README, bundle + PNG +
  report.

## 10. Resolved questions (verdict answers, recorded)

Q1. Pause and wait by default; variant B only on permanent unavailability
    via separate approval (section: Variant B).
Q2. Thresholds provisional + pinned Thai tokenizer, sequence-aware
    similarity, whole-scenario AND per-line, "operational" label
    (section 5).
Q3. "Stricter wording wins" REJECTED: agreement after cross-review
    freezes; persistent disagreement = CRITERIA_UNRESOLVED, category
    blocked, others continue (Phase 1).
Q4. Execution eligibility moved OUT of frozen content into an external
    record (sections 3.2, 7.3).

## 11. What this spec deliberately does NOT do

- No Thai number is ever a quality claim.
- No authoring yet; no code yet.
- Does not unblock ClaimView activation (C20), TLS (A18.3), or C19 itself
  (language lane).
- Does not touch reader_eval, the dev set, or the owner-authored path.
- A future human-validated set, if it ever exists, becomes the quality
  instrument; this set stays the breakage instrument.
