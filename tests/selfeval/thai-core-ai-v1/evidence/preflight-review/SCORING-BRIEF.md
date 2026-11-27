# Gemini preflight-v2 - independent reviewer scoring brief

You are one of the two named preflight reviewers (spec v2.5 section
4.2). Score INDEPENDENTLY from the recorded raw outputs. Do not
coordinate with the other reviewer. A scoring decision you cannot make
cleanly is a disagreement path: the category FAILS pending a new,
agreed assessment (fail-pending-reassessment). There is no discretion
to negotiate an ambiguous output into a pass.

## Materials (all in this package)

- raw/preflight-<category>-s1.txt - the 7 raw Gemini responses,
  verbatim, one per session, hash-pinned (SHA256SUMS).
- session_log.md - per-session model label ("Auto", displayed,
  self-reported by the service, unverified), dates, chat URLs.
- order.json - opaque id (pf-01..pf-05) to example-id mapping and the
  shuffled presentation order per batch.
- prompts/preflight/pf-<category>.txt - the exact prompts sent
  (pinned template v2 + frozen Part 3 examples).
- SHA256SUMS - hashes of prompts and templates; raw-file hashes are
  listed at the bottom of this brief.

## Frozen expected annotations (criteria v1.4 Part 3; per category,
## all 5 examples in the category share one expected tuple)

- recall: {"epistemic": "supported", "action": "answer"}
- unknown: {"epistemic": "unknown", "action": "abstain"}
- contradiction: {"epistemic": "contradicted", "action": "answer"}
- ambiguity: {"epistemic": "ambiguous", "action": "clarify"}
- teach: {"epistemic": "supported", "action": "acknowledge"}
- forget: {"epistemic": "unknown", "action": "acknowledge"}
- correction: {"epistemic": "supported", "action": "acknowledge"}

The expected tuple for a specific example follows from its category
(order.json maps each pf-NN back to gemini-preflight-<category>-N).
The full example texts are in the frozen criteria Part 3 and visible
in the prompt files themselves.

## Scoring rules (spec 4.2 + criteria Part 2, deterministic)

Per category, three dimensions:

1. STRUCTURAL COMPLIANCE - must be 5/5. For each of the 5 examples:
   output has the item id on its own line followed by a JSON code block
   containing exactly ONE JSON object; exactly the two required fields
   "epistemic" and "action" plus optional "rationale" (a NON-EMPTY
   string when present, omitted entirely when unused); no other fields;
   no missing decision. One miss fails the category.
2. INSTRUCTION COMPLIANCE - must be 5/5. The annotation invents no
   facts not derivable from the example text and the instructions;
   output items are in the order given; nothing else is added.
   Rationale text is never scored, but a rationale introducing
   unsupported scenario facts fails the example. One invented fact
   fails the category.
3. RUBRIC-APPLICATION CONSISTENCY - at least 4/5 examples match the
   frozen expected tuple. The decision fields must emit the EXACT
   ENGLISH ENUM TOKENS after normalization-only equivalence (Unicode
   NFC, whitespace folding, case folding). NO alias tokens. Any other
   formulation is a mismatch, not a judgment call. Record mismatched
   examples and the raw output either way.

Category PASS = all three dimensions pass under your scoring. The gate
passes a category only when BOTH reviewers pass it.

## What a PASS means (required honesty wording)

A passed preflight is STRUCTURAL PROCESS EVIDENCE ONLY - proof of
rubric-following under the pinned template. It is never evidence of
Thai semantic reliability, and never independent category recognition.

## Observed anomaly, recorded (not a scoring input)

The teach and correction sessions returned byte-identical raw files
(sha256 939235bfa8f7483dd53e3a5c13e6e92e8b9221d48dd39a9d0afd599037750706).
Re-capture from each session's own chat URL reproduced the identical
bytes, and the runner confirmed on each live page that both sessions
visibly show supported/acknowledge x5 (distinct chat titles per
session). Recorded as OBSERVED CROSS-SESSION CONSISTENCY between two
categories that share the same expected tuple, not a capture error.
Both files remain in the package as separate per-session artifacts.

## Raw file hashes (sha256)

- preflight-recall-s1.txt: b4d0946dbecf6636c7ea502364a05558e162ec173ada53b4beec375280ae5aaf
- preflight-unknown-s1.txt: 819a9894320021154efd601725e37169559a6dd3ffeef486fe897e47b23c4b86
- preflight-contradiction-s1.txt: a92459f5c3e8f681b1073f8e137ed84ad0e203fb787f284fabb8214560ed3226
- preflight-ambiguity-s1.txt: 82ff9b4d6aea0b2cdb22afa8cce6a901da38aa3f27e9fc6ecf98962aff241ad3
- preflight-teach-s1.txt: 939235bfa8f7483dd53e3a5c13e6e92e8b9221d48dd39a9d0afd599037750706
- preflight-forget-s1.txt: bc13be19198af9287f732e5491fb7a36f6925f5d7e86e633b747f9e25871f338
- preflight-correction-s1.txt: 939235bfa8f7483dd53e3a5c13e6e92e8b9221d48dd39a9d0afd599037750706

## Report back

Per category: structural x/5, instruction x/5, rubric x/5, verdict
PASS/FAIL, one line of reasoning per failure (if any), plus your
reviewer identity (family, model, date). Label your report: AI-scored,
part of an AI-authored / not human-validated pipeline.
