# thai-core-ai-v1 - CONTENT FREEZE attestation (spec v2.5 section 6)

Date: 2026-11-27. Label: AI เขียน / not human-validated.
Status transition attested: AI_AUTHORED_REVIEW -> AI_AUTHORED_CONTENT_FROZEN.
Authority basis: Ash's 22 Nov review delegation + 26 Nov "continue all";
routed via main. Everything attested here is AI-authored, AI-annotated
and AI-gated; this attestation is a PROCESS record, never a quality
claim about the agent or about Thai.

## Pinned artifacts (all sha256 over file bytes, as committed)

Frozen set:
- Manifest  tests/selfeval/thai-core-ai-v1/thai-core-ai-v1.manifest.json
  5c318e3b48398ceec0dca1770dafcc82dc32dcebe729fd6eaa31d58ff748d259
  (70 items, 63 scored, 7 unresolved, status AI_AUTHORED_CONTENT_FROZEN)
- Scenario corpus  tests/selfeval/thai-core-ai-v1/thai-core-ai-v1.corpus.json
  923dfd3d1ea48a80aacacd38ec24bb1da8c26879cddb95104a0338ff9e6606e2
- Exclusion ledger  tests/selfeval/thai-core-ai-v1/thai-core-ai-v1.exclusions.json
  f879efeaa6f89460e19bed686e5c24fef06d4c69f7d23e8902c1eecc05181888
  (genesis only, 0 exclusions, ledger head
  9cfde10225d97257b3ea9426874412c64d6cd92ce91be36e3db9c442ccc15416,
  chained to the frozen manifest hash)

Gate inputs and contracts:
- Variation plan v12.1 PINNED  docs/thai/thai-core-phase2-variation-plan-v12.1-PINNED.md
  01d6b719483d2e6f47f0751b3311423ba6cd275948ba6f9bc199283090a130b3
- Criteria v1 FROZEN (v1.4 file)  docs/thai/thai-core-phase1-criteria-v1.4-claude.md
  241612cab5f3efbec8eee2562e2850680a8a262186132cbe4af8ee6af7a2dd18
- Spec v2.5  docs/thai/thai-core-ai-authored-spec-v2.5.md
  2fdad5b69c69428f684e0335d3294e5e50d0241e7581d625023cf8215cd070bd
- Author briefs  docs/thai/thai-phase3-author-brief-gpt.md,
  docs/thai/thai-phase3-author-brief-claude.md
- Authoring slot checker  scripts/thai-phase2-slot-check.py
  80f32a924963c21a2e74401805fdff1a593998306f8656a93a63caafce9594cb
- Phase 3 item checker  scripts/thai-phase3-item-check.py
  661a1fc4ea3de4a4c0a48fe44459e81d7eea628faeff5ad600bd59e8ba798d42

Phase 4 annotation:
- Session/annotation decision log  tests/selfeval/thai-core-ai-v1/thai-core-ai-v1.annotations.json
  cd04b32dec5464f10c71270f49b346d2d7b495e35a0e7c46e3c5d057e62400ae
  (202 records: 101 Gemini + 50 GPT + 51 Claude, 21 sessions)
- Corpus prompt template v1.1 (annotator contract, both families
  GO-with-folds)  evidence copies in corpus-gemini/ and cross-claude/
  0ff7e325ac7a98f20a16dce37afc1560e98f5ae1b5127148b8372d24093eccf4
- Raw-response evidence: per-bundle session logs, order.json and
  SHA256SUMS files under tests/selfeval/thai-core-ai-v1/evidence/
  {preflight, preflight-review, corpus-gemini, cross-gpt, cross-claude}/;
  each session log pins its batch files' hashes and chat URLs, and each
  SHA256SUMS pins every raw annotation file. Key pins:
  corpus-gemini/SHA256SUMS 655d960e43f50a322d3e9ce4ef44550342b510ebe38405039d39158c1bbad757
  cross-gpt/SHA256SUMS     87f37f39735976b5165fcdf60338e1ee0094a513de1440c6b6bdcb425573def9
  cross-claude/SHA256SUMS  c877b94f28235fbcca27238483e62ad8622049d9c12dc4a0f41c88cdfdf01c6d
- Preflight review score sheets  evidence/preflight-review/
  gpt-score-sheet.md 63a51536bbeb1e6e172e304541ba3ac5aa52308e8212c3186c0f695a611a0938
  claude-score-sheet.md 46b95ac592129f073e90dea0321ae1828f77afc28cfaf7e2105b343b4428a920

Phase 6 gates:
- External checker (spec 3.1-3.5 / 4.4-4.6 / 6 rules)
  scripts/thai-ai-check.py  e991b5e07d5c2c98cf220014df72fb535e72b1f22200e1bcc7275d9dfa230b03
  Result: AI-CHECK CLEAN: 70 items, 63 scored, 7 unresolved,
  202 annotation records, 21 sessions.
- Overlap gate  scripts/thai-overlap-check.py
  c493f37d038b02a82aff697ea6fc0e4075eab96f96b8bd0a011b0cc8a8071da6
  Overlap report  tests/selfeval/thai-core-ai-v1/thai-core-ai-v1.overlap-report.json
  ed2522b8276dd0f1c9f7dea5fab1609e0d0f50883a7c8b7a5ac07044d181b8bc
  Inputs pinned: corpus hash above; dev set tests/selfeval/thai-dev-ai-v1.json
  da113647b1c1b7d86736cfb627ca701d8b2a4e8cc4162294b0c67aa0e0821c64;
  tokenizer pins (pythainlp 5.4.0, engine newmm, default dict) recorded
  inside the report.
  Result: 53,452 comparisons, 0 rejections, 6 flags, namespaces
  disjoint; every flag kept-with-reason (short generic pronoun probes
  contained in longer unrelated scenarios; Jaccard 0.04-0.50, sequence
  0.04-0.53, all far below flag thresholds; not semantic duplicates).
- Pipeline-health report  docs/thai/thai-core-ai-v1-phase4-5-report.md
  (this freeze's Phase 4/5 record)

Evaluation harness identity (source pinned; EXECUTION GATED):
- scripts/thai-core-harness.py
  906026955f6d81bce449486cf3cd23e2af0362579a776cbbb739c58b91571ae9
  The harness consumes the frozen corpus, runs one agent/repl.holy
  subprocess per scored item and emits replies-vXXX.json extended with
  a build field. It refuses to run without an external EXECUTION
  ELIGIBILITY record (spec 7.3) pinning this corpus hash; verified to
  refuse when no such record exists. It has never executed the frozen
  set, and parity testing never uses this set.

## Interpretation disclosure

"Checker clean" (Phase 6 gates) is satisfied by the EXTERNAL checker
scripts/thai-ai-check.py above. Spec section 9's in-agent checker
(agent/selfeval.holy thai-check extension) plus evaluation-harness
execution plus test extension are the separately gated step: the
harness SOURCE is written and hash-pinned now, its EXECUTION stays
gated on C19 eligibility; the in-agent checker extension is not part
of this freeze and remains open for the gated step. No agent code,
compiler, seed or test file was touched by this change.

## Freeze rules now in force (spec section 6)

Any change to the frozen set requires a new corpus version with its
own full evidence package; a correction during evaluation must leave
the broken item reproducible; the exclusion ledger is the only
mutation channel, append-only, evidence-linked and hash-chained.

## Anchor

This attestation is anchored immutably by the git commit containing it
on branch thai-core-ai-v1; the containing commit hash is recorded in
the accompanying report to main.
