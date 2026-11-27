# thai-core-ai-v1 - Phase 4 (annotation) + Phase 5 (resolution) report

Date: 2026-11-27. Label: AI เขียน / not human-validated. Everything in
this report is AI-authored, AI-annotated and AI-scored; nothing here is
a quality claim about the agent or about Thai. Pipeline-health numbers
only (spec v2.5 section 8). Authority basis: Ash's 22 Nov review
delegation + 26 Nov "continue all"; routed via main.

## Phase 4 - annotation (variant A)

Preflight gate (spec 4.2, protocol preflight-v2, frozen criteria Part
3 examples): all 7 categories PASS under BOTH reviewers (GPT and
Claude, each 5/5 structural, 5/5 instruction, 5/5 rubric on every
category, scored independently from raw outputs). Interpretation:
structural process evidence only - rubric-following under the pinned
template, never Thai semantic reliability.

Corpus annotation (protocol corpus-v1, template v1.1 sha256
0ff7e325ac7a98f20a16dce37afc1560e98f5ae1b5127148b8372d24093eccf4,
both families GO-with-folds, folds recorded in
thai-phase4-corpus-bundle PIN-RECORD): 202 annotation decision records
(tests/selfeval/thai-core-ai-v1/thai-core-ai-v1.annotations.json,
sha256 cd04b32dec5464f10c71270f49b346d2d7b495e35a0e7c46e3c5d057e62400ae):
- Gemini (all 70 items): 101 scored-turn annotations, 7 batches,
  model label "Auto" (displayed, self-reported, unverified), free tier.
- GPT (Claude-authored 35): 50 annotations, 7 batches, "ChatGPT (no
  model name displayed; Think ON)", free tier.
- Claude (GPT-authored 35): 51 annotations, 7 batches, "Sonnet 5.5
  Medium" (displayed, self-reported, unverified), free tier.
All 21 sessions: fresh chats, one at a time, prompts pasted verbatim,
raw responses captured unedited, all raw-file sha256s verified against
the session logs. No quota walls; no batch spanned sessions.

Structural validation (pair rule from corpus-v1): every batch emitted
exactly its marked (id, turn) pairs, once each - 101/101 Gemini, 50/50
GPT, 51/51 Claude. Closed schema throughout; 53 optional rationale
fields (never scored).

Recorded anomalies: (1) preflight teach/correction sessions returned
byte-identical outputs; re-captured from each session's own chat URL
with identical bytes and live-page confirmation; recorded as observed
cross-session consistency (identical expected tuple, identical
formatting), scored as separate per-session artifacts. (2) Claude
cross-annotation runner briefly saved a stale clipboard capture on two
early batches, caught and re-copied; validated per-batch pair coverage
against order.json confirms no cross-batch contamination.

## Disagreement rates (per pair AND per category, spec variant A)

GPT+Gemini (family A items): 47/50 pairs agree (94.0%).
  recall 5/5, teach 7/7, contradiction 5/5, forget 13/13,
  correction 9/10, ambiguity 4/5, unknown 4/5.
Claude+Gemini (family B items): 47/51 pairs agree (92.2%).
  recall 5/5, teach 8/8, contradiction 5/5, correction 9/10,
  forget 12/13, ambiguity 4/5, unknown 4/5.

## Phase 5 - resolution (spec 4.4)

63 items scored (annotator pair agrees on every scored turn).
7 items unresolved, all "annotator-disagreement":
ambiguity-S02 (t2), ambiguity-S03 (t2), unknown-S03 (t1), unknown-S04
(t1), correction-S04 (t2), correction-S10 (t6), forget-S09 (t7).
Five of seven sit on the G5 unknown/ambiguous/missing-referent
boundary; two are correction/forget state-tracking turns.
0 items under "no-independent-adjudicator": the AI-path item schema
carries no critical/ambiguous flags (the author briefs had no flag
mechanism); the vacuous case is recorded explicitly.
One scored item carries a divergence note: ambiguity-S01 - both
annotators agreed (unknown/abstain) AGAINST the author target
(ambiguous/clarify); the agreed annotation is the gold under 4.4 and
the author target stays recorded in the corpus for the Phase 6 audit.

## Pipeline health (section 8)

- Authoring: 70/70 slots delivered across 2 families; 2 items rejected
  at the structural gate (register violations) and revised by their
  author family; final set 0 checker errors, 0 warnings.
- Unresolved pool: 7 items, single reason class.
- Overlap gate: 0 rejections, 6 flags (all kept-with-reason); see the
  overlap report.
- Exclusion ledger: genesis only, 0 exclusions.
- Quota interruptions: none in any annotation session.
- Mark-pattern freeze check (Claude A-fold): recorded per bundle; the
  teach (1 vs 2 marks) and forget (2 vs 3 marks) profiles separate
  label profiles within their batches, mirroring scenario-visible
  structure; disclosed, judged no additional leak.

## What this set is

A breakage-catching instrument under CONTENT FREEZE candidacy. No
per-item results exist; no execution has happened; execution requires
the external eligibility record (spec 7.3) after C19 parity on the
SEPARATE Thai serialization test corpus.
