---
id: l0-failure-attribution-229
status: L0 artifact v1 (2026-11-27)
---
# L0: failure attribution for the frozen Thai eval (0 parseable turns)

Method: classify every turn of the frozen thai-core-ai-v1 corpus
(70 items, 252 turns; 63 items / 229 turns executed by the gated
harness at replies-v002) against what the agent's grammar supports
TODAY. Mechanical classification, no LLM, reproducible from the
frozen corpus bytes. AI-authored / not human-validated.

## Counts

- teach frames "จำไว้ว่า..." (จำ...): 144/252
- other natural sentences: 104/252
- turns containing a question shape the grammar knows today
  (คืออะไร / อยู่ไหน / หมายความว่าอะไร / หรือไม่ / ไหม / spaced คือ/เป็น): 4/252
- turns with a register particle (ครับ/ค่ะ): 120
- turns containing spaces: 128 (about half; Thai here is mostly unspaced)

By category: forget 50, correction 41, recall 39, contradiction 33,
teach 32, unknown 29, ambiguity 28.

## Conclusion (answers Claude's consult pushback)

The 0/229 is GRAMMAR-side first, not segmentation-side:

1. Today 100% of turns fail at parse: the agent has no Thai teach
   command (จำไว้ว่า), no Thai question words of the corpus's shapes
   (เป็นอะไรกับ, มีสีอะไร, อยู่ที่ไหน), no register-particle stripping,
   no kinship/possessive semantics (ป้าของผม).
2. Segmentation is the SECOND blocker: even with perfect Thai grammar
   frames, the roughly half of turns without spaces need dictionary
   segmentation to extract subjects and values.
3. Only 4/252 turns would parse even with a perfect dictionary and no
   grammar work.

Sequencing consequence: R3 grammar work (Thai command/question frames,
particles, pronouns) is the first lever for the eval number; the
L1.1 lexicon + segmentation artifact lands right behind it inside R3.
This matches both consults' suspicion and keeps L1.1 from claiming a
parse-rate move it cannot cause.
