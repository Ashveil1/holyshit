# thai-core v1 (AI path) - FREEZE ATTESTATION (Phase 2 entry: variation plan pin)

**AI เขียน / not human-validated.** No quality claim about the
evaluation set, no capability claim about any agent. This file makes
tamper-evident WHAT was pinned and under which review outcomes; it
asserts nothing about Thai naturalness or correctness.

This is the Phase 2 entry of the spec 6.1 freeze attestation. Later
phases append their pins (manifest content, scenario corpus,
exclusion ledger head, session log, annotation decision log,
raw-response evidence files, overlap report, prompt templates,
evaluation harness source/build hash) at CONTENT FREEZE; each
extension is committed and re-anchored.

## Pins (sha256 of the committed files)

- Variation plan v12.1 (PINNED):
  docs/thai/thai-core-phase2-variation-plan-v12.1-PINNED.md
  01d6b719483d2e6f47f0751b3311423ba6cd275948ba6f9bc199283090a130b3
- Slot checker (plan version v12.1 recorded beside the script
  docstring's v12.1):
  scripts/thai-phase2-slot-check.py
  80f32a924963c21a2e74401805fdff1a593998306f8656a93a63caafce9594cb
- Criteria v1 (FROZEN, Phase 1 pin carried forward):
  thai-core-phase1-criteria v1.4
  241612cab5f3efbec8eee2562e2850680a8a262186132cbe4af8ee6af7a2dd18

## Review outcomes behind this pin

- GPT: GO to hash-pinning on v12 (26 Nov 2026), no blockers; v12.1
  applied its four text-only cleanups. Verbatim reply retained in the
  review evidence (gpt_v12_reply-b185a529.md).
- Claude: GO to hash-pinning on v12.1 (26 Nov 2026), no blockers;
  re-ran the checker and --verify-plan itself (exit 0, hashes match).
  Verbatim reply retained in the review evidence
  (claude-v12.1-go-no-go-reply-verbatim-74f8777e.txt).
- Both families' GO covers PINNING ONLY. Neither family validated the
  Thai, and neither GO is a quality or naturalness claim.

## Validation evidence (run on the committed files)

- python3 scripts/thai-phase2-slot-check.py
  -> "ok all slot-table checks pass (7 categories x 10 slots)"
- python3 scripts/thai-phase2-slot-check.py --verify-plan
  docs/thai/thai-core-phase2-variation-plan-v12.1-PINNED.md
  -> "verify-plan ok: section 4.8 matches --emit; canonical bytes ok
     (plan + script)"
- Draft-to-pinned diff (section 10 step 3):
  docs/thai/thai-phase2-plan-v12.1-draft-to-pinned.diff
  (status header removed per section 10 step 1; nothing else changed)
- Non-normative review companion (not pinned, not binding):
  docs/thai/thai-phase2-variation-plan-review-history.md

## Editorial nits recorded (per Claude's GO non-blockings; NOT edited)

- Leftover "spot audit" wording survives in places in the plan body
  and checker comments; the governing scope is section 5 (all 28
  pronoun slots count-validated, 15 pronoun+decoy slots
  discourse-audited). Recorded, not edited.
- The antecedent-table loop in the checker is a tautological
  consistency guard, NOT an independent check; it is never described
  as one.
- Person-pronoun coverage is 0/14 (disclosed in plan section 9);
  reports must never claim person-pronoun coverage.

## Authority basis (evidence outside this file)

Ash's 22 Nov delegation of the thai-core review loop to Instinct+GPT
with Claude review, and 26 Nov "continue all" covering the hs ai
lane, relayed through the main agent. Both families' GO verdicts were
relayed as verbatim files, advice only; the pin decision followed the
spec v2.5 process gate (both families GO + checker pass).

## Anchor

This attestation is committed to the holyshit repo. The containing
GIT COMMIT HASH is its anchor and is recorded in the Phase 2 pin
milestone report (the file cannot contain its own commit hash). The
attestation is never the unpinned authority for the other pins.
