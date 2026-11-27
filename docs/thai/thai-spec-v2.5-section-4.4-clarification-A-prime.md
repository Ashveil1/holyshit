# Spec v2.5 section 4.4 clarification + A' per-item rollup (RATIFIED 2026-11-27)

Label: AI-authored / not human-validated. Process record only.
Status: RATIFIED. Rulings from both consult families (GPT and Claude,
2026-11-27, verbatim replies retained by main; chat URLs recorded in
main's relay) both chose option A'. This document is the formal
clarification of spec v2.5 section 4.4 and the definition of the A'
rollup. It amends interpretation only; no frozen artifact changes.

## 1. Section 4.4 clarified: "critical/ambiguous" is an ITEM-LEVEL FLAG

For the AI path, "critical/ambiguous" in section 4.4 refers to an
explicit author-declared item-level criticality or ambiguity flag. It
does NOT refer to the annotation-level epistemic label value
"ambiguous".

- An annotation record whose label is (ambiguous, clarify) does NOT, by
  itself, consign the item to the unresolved pool. In the ambiguity
  category, (ambiguous, clarify) is the category's intended gold label:
  it is scored content.
- An item carrying an explicit critical/ambiguous flag goes to the
  unresolved pool with reason "no-independent-adjudicator" even when
  both annotators agree. No such flag mechanism existed in the v1
  author briefs.
- LEGACY (thai-core-ai-v1): the absence of an item-level flag field is
  treated as "no declared flag under the v1 process". This is a
  recorded process fact, NOT an independent human assessment that every
  item is substantively noncritical. The v1 outcome of zero
  no-independent-adjudicator items is exactly this: zero declared
  item-level flags under the v1 process. Known limitation, recorded
  explicitly (per both rulings: do not paper over it).
- FUTURE corpus versions: the author briefs gain an explicit
  critical/ambiguous flag field, making the class non-vacuous.

Rationale on record: section 4.4's own sentence names flags ("Authors
are told in the brief that critical/ambiguous flags consign an item to
the unresolved pool on the AI path"); the scoring condition speaks of
the ITEM ("the item is not critical/ambiguous"); and the label reading
collapses the ambiguity category (1 of 10 scorable), a validity defect,
not conservatism. The label-based trigger in the merged in-agent
checker (#454) is classified as an emergent implementation choice,
absent contemporaneous decision evidence; the language agent is asked
for one line on the record about which it was.

## 2. A' rollup: per-(id, turn) records, deterministic item rollup

The canonical thai-core-ai-v1 artifacts stay the FIVE frozen files
(commit d800d43). The pinned corpus template v1.1 pair rule (sha256
0ff7e325ac7a98f20a16dce37afc1560e98f5ae1b5127148b8372d24093eccf4) is
authoritative for annotation granularity. The in-agent checker adapts
to the frozen set, never the reverse.

Rollup rules (normative):

| Rule | Required behavior |
| --- | --- |
| Pair completeness | Exactly two annotation records for each expected (id, turn) scored pair; missing, duplicate or incomplete pairs are never silently treated as agreement |
| Annotator independence | The two records of a pair belong to distinct annotator families, neither being the item's author family (family-level author exclusion) |
| Pair agreement | The two records' complete label tuples compare equal |
| Item agreement | Agreement on EVERY scored target turn of the item; a multi-turn item never passes on a majority |
| Disagreement | Any disagreeing or incomplete pair -> item unresolved, reason "annotator-disagreement" |
| Flag rule | An item with a declared critical/ambiguous flag -> unresolved, reason "no-independent-adjudicator", even on full agreement |

"Variant A = exactly two annotations per item" is replaced by "two
family-distinct annotation records per (id, turn) scored pair".

## 3. Derived checker-consumable manifest

A single checker-consumable manifest is produced as a PINNED DERIVED
VIEW, generated deterministically by scripts/thai-derived-view.py from
the five frozen files. It is marked derived and non-normative, records
the source commit (d800d43) and the sha256 of every input, and never
replaces or mutates the canonical artifacts. The derivation script's
own sha256 is pinned in the execution eligibility record (the derived
view is never an unpinned step between the frozen data and a run).

## 4. Consequence for thai-core-ai-v1

Dispositions are unchanged: 63 scored, 7 unresolved (ambiguity-S02,
ambiguity-S03, unknown-S03, unknown-S04, correction-S04, correction-S10,
forget-S09; all annotator-disagreement). Ambiguity category: 8 scored
of 10. Eligibility and the first harness run remain blocked until the
checker alignment PR lands, the derived view verifies clean against the
aligned checker with these exact counts, and the eligibility record is
written.
