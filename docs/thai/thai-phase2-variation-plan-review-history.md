# thai-core Phase 2 variation plan - REVIEW FOLD-IN HISTORY (NON-NORMATIVE)

This file is review evidence only. It is NOT pinned, NOT hash-attested,
and NOT binding on authors. The governing text is the current plan
(sections 1-10 and Annex A). Where this history disagrees with the
current plan (it records superseded intermediate states), the plan wins.

## 0. Changes from v5 (GPT re-review fold-in map)

- B1 (author still confounded with entity type and abstract domain -
  person items were A 12 / B 2, every size item B, every occupation
  item A): the allocation matrix was re-searched with the added
  set-wide constraints and the checker now enforces them: each
  entity type exactly 7/7 between authors; registers differ by at
  most 1 per register set-wide (plain 14/14, ครับ 11/10, ค่ะ/คะ
  10/11); every multi-item abstract domain split as evenly as its
  total permits (color 3/3, taste 2/3, age 1/2, size 1/2, occupation
  1/1; the singleton count domain is exempt). Per-category
  constraints (5 items, 2/2/1 lengths, all 3 registers, even
  multi-item bin splits) are unchanged. N=70 and all variation
  assignments are unchanged; only the Author column moved.
- B2 (G-AX5 attribute shape omitted taste and occupation; beverage
  status of the food bin unstated): G-AX5's attribute shape now
  lists all six abstract domains (color, age, size, count, taste,
  occupation), and G-AX3a defines the food entity bin as including
  beverages, matching Annex A's "food or drink".
- Non-blocking register balance: folded into B1's set-wide register
  constraint (at most 1 apart per register).
- Non-blocking checker coverage: the checker now carries the
  entity/domain/register author-balance checks (it previously had
  none across those axes).
- Process: Claude's review of this line remains a pinning
  prerequisite (carried from v3/v4/v5).

## 0a. Changes from v4 (GPT re-review fold-in map)

- B1 (odd/even author allocation confounded author with subtype and
  register): replaced by a per-category ALLOCATION MATRIX, pinned in
  the tables (Author column) and checker-validated. Per category,
  each family authors exactly 5 items with 2 short / 2 medium / 1
  long, sees all three registers, and splits every multi-item
  subtype bin - plus contradiction's declarative/question forms,
  teach's copula/possession constructions, forget's request
  constructions and correction's multi-item markers - as evenly as
  the bin's count permits. Singleton bins cannot be split and are
  exempt. The matrix was found by exhaustive search over the pinned
  tables; the checker verifies all conditions directly.
- B2 (G-AX3b vs Annex A domain mismatch): the authoritative abstract
  domain list is now color, age, size, count, taste, occupation -
  "day" is removed (unused) and spiciness is defined as a value
  within the taste domain. Every abstract slot's exact domain is
  pinned in the table's Abstract value column and in the checker;
  Annex A now explicitly lists occupation and taste (including
  spiciness) as supported attribute values.
- N1 (pin exact abstract-domain counts): domains are pinned per slot
  (above) and set-wide totals are pinned: color 6, taste 5, age 3,
  size 3, occupation 2, count 1 = 20 abstract-valued items; the
  checker verifies the totals.
- Process: Claude's review of this line remains a pinning
  prerequisite (carried from v3/v4).

## 0b. Changes from v3 (GPT re-review fold-in map)

- B1 (binding pronoun inventory not updated in v3 - the v3 change log
  claimed the extension but G-AX4 itself still read "animals and
  objects"): G-AX4 now authoritatively reads มัน/พวกมัน for ALL
  non-person entities (animals, objects, places, food); this is the
  only place the inventory is defined.
- B2 (register audit rule was unachievable under the pinned tables):
  register assignment is now PER CATEGORY (still 4/3/3 each), chosen
  by exhaustive search so every multi-item audit bin spans >=2
  registers within its category and every slot sees >=2 (in fact 3)
  registers across the set. Section 5 defines the audit units
  precisely: subtype bins, shape bins, request-construction/marker
  bins, and target labels; singletons are reported descriptively;
  multi-item bins must span >=2 registers. The checker verifies the
  tables satisfy this by construction.
- B3 (forget decoy vs unrelated-fact probe target): G-AX7 and 4.6
  now state explicitly: in every one-of-several forget item, the
  unrelated-fact probe asks a different retained fact OF THE ORIGINAL
  TARGET SUBJECT; the decoy's own fact is NEVER the correct answer to
  any scored probe. Slot notes reworded to match.
- N2: trap positions pinned: S05 + S08 trap BEFORE the target facts,
  S07 + S09 trap AFTER (checker-verified).
- N3: author-to-slot allocation interleaved (odd slots family A,
  even slots family B per category; which family is A/B is recorded
  at Phase 3). SUPERSEDED in v5 by the per-category allocation matrix
  (section 0, B1).
- N4: limitations now state the checker proves only its implemented
  structural checks - not Thai naturalness, not correct authoring,
  not Phase 6 outcomes.
- B4 (process): Claude's review of this line remains a pinning
  prerequisite.

## 0c. Changes from v2 (GPT re-review fold-in map)

- B1 (decoys on short slots): a decoy carries its OWN taught setup
  fact, so decoy items are medium/long ONLY. Moved: recall S03->S06,
  unknown S03->S08 (subtype swap: missing-referent moved to S03,
  untaught-relation+trap to S08), contradiction S02->S06,
  ambiguity S03->S07, correction S03->S05. The checker now REJECTS a
  decoy on a short slot.
- B4 (entity type vs value domain): G-AX3 split into G-AX3a entity
  types (5 bins, exactly 2 slots each) and G-AX3b value domains
  (abstract values: occupation/color/size/count/day/taste; 1-4
  abstract-valued items per category; occupation values only on
  person hosts). New "Abstract value" column in every slot table;
  checker-enforced.
- B2 (unknown S08 wording + ambiguity S08 pronoun): section 3.9
  exemptions are now unknown S03 and S04 (both short,
  missing-referent, trap-free). Pronoun inventory extended:
  มัน/พวกมัน covers ALL non-person entities (animals, objects,
  places, food), so two-place and two-food antecedent pairs are
  authorable.
- B3 (contradiction scored turn): the scored target is the agent's
  reply WITHIN the same turn as the conflicting assertion (the
  instruction-under-test), expected {contradicted, answer}; no
  separate follow-up turn exists in this category.
- B5 (ambiguity defensibility): restored the v1 rule explicitly and
  per slot: the setup + probe context MUST make both referents/
  readings independently identifiable (criteria clause 4 + G5).
- N1: forget phrasing bins renamed REQUEST-CONSTRUCTION bins (verb
  choice and politeness framing are not separated axes; the four
  constructions are pinned as-is).
- N2: G-AX7 now states a decoy's value is never probed and need not
  carry a scored probe; in teach the decoy fact is never the
  instruction-under-test target.
- N3: the Phase 6 register audit now has a failure rule (section 5):
  the audit FAILS if any subtype or target label appears exclusively
  in one register; no statistical-independence claim is made from a
  70-item set.
- N4: recall slot notes write "intervening 2-3 turns" on every
  intervening slot (S05, S07-S10).
- Checker extended: decoy-off-short, entity-type exact pairs,
  abstract-value count/shape/host rules, exemption consistency,
  teach follow-up count, forget subtype-by-length.

## 0b. Changes from v1 (review fold-in map)

GPT blockers B1-B8 and Claude blockers B1-B10 are folded as follows:

- Cross-axis conflicts (GPT B1, Claude B1): G-AX2 redefined so LENGTH
  is determined ONLY by setup-fact count (section 3); the recall
  long-item parenthetical is deleted; forget is re-binned
  (4 single-fact + 6 one-of-several); ambiguity reverts to the global
  4/4/2 with a forced subtype-by-length mapping (polysemy = the 4
  short slots). A precedence clause and a single overrides list
  (section 3.9) replace ad-hoc exceptions: with the new definitions,
  NO category override remains.
- Undefined terms (GPT B3, Claude B4): section 2 defines turn, setup
  turn, instruction-under-test, follow-up probe, scored turn, taught
  fact, intervening turn. Section 5 pins the expected label of EVERY
  scored turn per category; multiple scored turns per scenario are
  explicit.
- "Rotate" undefined (GPT B4, Claude B3): rotation is replaced by
  pinned 10-row slot tables per category (S01-S10), generated and
  mechanically checked by scripts/thai-phase2-slot-check.py
  (its sha256 joins the attestation). Entity types: 5 bins, exactly
  2 slots each. Shapes: >=3 distinct, max 5 per shape.
- Negation (GPT B5, Claude B2): G-AX6 now applies to contradiction and
  correction ONLY (forget dropped: อย่า is prohibitive, not a form in
  the closed list, and Annex A allows no taught negative facts).
  Correction's negative-frame markers are split by relation
  (ไม่ใช่ / ไม่มี / ไม่ได้อยู่) giving 3 distinct forms; contradiction
  carries 2 forms with pinned slots. ใช่ไหม is a confirmation-seeking
  question form, never a negation form.
- Register (GPT B6, Claude B8): register is PER SCENARIO, constant
  across the scenario's user turns; bins are {ครับ}, {ค่ะ/คะ},
  {none of ครับ/ค่ะ/คะ} (question-final คะ counts as ค่ะ). The bins
  imply NO speaker gender or identity. Plain forbids only
  ครับ/ค่ะ/คะ; other particles are unconstrained. Registers are
  pre-assigned in the slot tables across lengths and subtypes; a
  final audit of register vs annotated target labels runs at Phase 6.
- Scenario isolation (GPT B7): every scenario runs in an isolated
  conversation with fresh memory (section 2).
- Overclaim (GPT B8, Claude B10): section 8 reworded - the plan
  constrains authors; the Phase 6 overlap gate is the enforcement.
- Anaphora (Claude B5): pronoun inventory {เขา (people),
  มัน/พวกมัน (animals/objects), พวกเขา}; เธอ is FORBIDDEN in user
  turns (reads as addressing the agent). Outside ambiguity items
  every pronoun MUST have exactly one defensible antecedent; the two
  unknown missing-referent items are exempt (zero antecedents) and
  never carry traps. Zero anaphora is declared OUT of scope (a stated
  limitation).
- Subtype traceability (Claude B6): every subtype names its frozen
  criteria clause. ไม่ใช่ X แต่เป็น Y IS a correction marker and is
  therefore FORBIDDEN inside contradiction items.
- Relation exclusivity (Claude B7): single-valued (subject, relation)
  everywhere; possession uses counts with classifiers or explicit
  ไม่มี; replacement values plainly incompatible (colors, sizes -
  never replace-vs-add ambiguous pairs).
- Non-exclusive bins (Claude B9): forget phrasing bins are by VERB
  (politeness framing orthogonal); the forget re-ask probe is
  UNIVERSAL (every item); correction post-correction probe is
  UNIVERSAL; "แก้ไข:(bare)" excludes the long form.
- Modal consistency (Claude): MUST/MAY used consistently; no MAY
  carries a fixed count.

Non-blocking items folded: decoy axis is now G-AX7 (exactly 4/10 per
category, so "a second entity exists" never predicts a label); author
allocation requires 5 items per category per family (N=70); unique
entity names across the set except intended same-name pairs;
fictional scope includes places (no real provinces/districts/villages,
no famous real animals/people, no names from criteria examples);
Thai naturalness rules (section 6); limitation sentence that axes are
coverage controls, not strata (section 9); pinning mechanics with
canonical bytes and self-hashing checker (section 10).

## Changes from v7 (GPT re-review fold-in map)

- B1 (person decoy is NOT guaranteed pronoun-class-distinct: มัน can
  refer to humans in informal Thai; ambiguity S07 could have had 3
  defensible antecedents): the G-AX4 pronoun+decoy rule is now
  DISCOURSE-LEVEL - the decoy's fact is taught and closed before the
  antecedent's introduction, never re-mentioned, and at the pronoun
  the antecedent is the most recent and only same-turn subject.
  Class distance (person decoys) is kept only as an extra margin.
  Unknown S09's pronoun is pinned before the trap fact appears.
  Checker enforces the discourse-unavailability pin in the notes.
- N1: ambiguity S08's มัน-for-places is named in G-AX4 as a narrow
  naturalness exception.
- No count, flag, allocation or assignment changed; notes and rule
  text only.

## Changes from v8 (GPT re-review fold-in map)

- B1 (unknown S09 contradicted condition (a)): the G-AX4 pronoun+decoy
  rule now explicitly permits BOTH safe orderings - decoy not yet
  introduced at the pronoun, or introduced earlier, explicitly
  closed, never reintroduced. S09's assignment is unchanged.
- B2 (discourse-unavailability not sufficiently established): the
  boundary is strengthened to an operational form - pronoun at most
  one turn from its antecedent, decoy absent from the pronoun's turn
  and the turn before, predicate-incompatibility margin where
  feasible - plus a binding author antecedent self-check (section 6
  rule 8), a Phase 6 spot audit of antecedent uniqueness on all 15
  pronoun+decoy slots (section 5), and a declared residual-risk
  limitation (section 9). Fallback recorded: a slot that cannot be
  authored safely drops and moves its decoy (4 per category kept) as
  a section-10 plan change. No slot needed the fallback; N=70, all
  allocations, flags and domains unchanged.

## Changes from v9 (GPT re-review fold-in map)

- B1 (spot-audit count 15 vs GPT's 14): verified against the tables -
  GPT's list omitted forget S09, which carries both the pronoun and
  decoy flags, so 15 is correct. Section 5 now enumerates all 15
  slots and the checker pins the pronoun+decoy set (PRONOUN_DECOY),
  so the count and the checker agree by construction. No flag
  changed.
- Non-blocking: the Phase 6 spot audit is now an explicit ACCEPTANCE
  GATE (failing item rejected and fixed before set acceptance).
- Non-blocking: the author self-check records ALL defensible
  antecedents a reader could entertain, not only the intended ones.
- N=70, categories, author split and the discourse design unchanged.

## Changes from v10 (GPT re-review fold-in map)

- B1 (rule 8 vs zero-antecedent exemptions): the antecedent-count
  expectation is now a single pinned table applied identically in
  G-AX4, section 6 rule 8, section 5 and the checker: exactly 0 on
  unknown S03+S04 (missing-referent), exactly 2 on ambiguity S07-S10,
  exactly 1 on every other pronoun slot. G-AX4's exactly-one rule now
  explicitly exempts S03+S04.
- B2 (same-name S09): the two-antecedent expectation on ambiguity's
  pronoun slots now names S09 explicitly (same-name pair = the two
  intended มัน candidates), no longer tied to the
  pronoun-2-antecedent subtype alone.
- No count, flag, allocation or assignment changed.

## Changes from v11 (GPT re-review fold-in map)

- B1 (Phase 6 audit scope undefined): section 5 now states explicitly
  that Phase 6 validates the pinned antecedent count on ALL 28
  pronoun slots (checker-pinned total) AND additionally performs the
  deeper discourse-unavailability audit on the 15 pronoun+decoy
  slots; both are acceptance gates.
- B2 (singular conditions vs two-antecedent items): G-AX4 now scopes
  "most recently introduced subject" and "only subject of its turn"
  to single-antecedent items; on ambiguity S07-S10 both intended
  candidates remain independently defensible by design, and the
  ordering/turn-absence conditions constrain only any additional
  decoy.
- No slot, allocation or count changes.

## Changes from v12 (GPT post-GO cleanups, v12.1)

- Duplicated "Changes from v11" block in this history file removed.
- Section 6 rule 8 wording: "spot audit" -> "audits" (section 5
  covers all 28 pronoun slots plus the 15-slot discourse audit).
- Section 5: the count check covers EVERY recorded pronoun
  occurrence, not one aggregate per slot.
- Naturalness limitations in section 9 (marginal มัน for places,
  skewed pronoun-host coverage) unchanged and visible.
- No rule, table, count or assignment changed.
