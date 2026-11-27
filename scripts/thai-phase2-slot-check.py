#!/usr/bin/env python3
"""thai-core Phase 2 variation plan v12.1: slot-table generator + checker.

Emits the seven 10-row slot tables (S01-S10 per category) as Markdown
and mechanically verifies every pinned constraint from the plan:
length 4/4/2, register 4/3/3, pronoun exactly 4 (with documented
exemptions), decoy exactly 4 AND only on medium/long slots (a decoy
carries its own taught setup fact), entity types (5 bins, exactly 2
each) counted independently from value domains (1-4 abstract-valued
items per category, occupation values only on person hosts), shapes
(>=3 distinct, max 5), entity x shape compatibility, register
independence from subtype, pronoun-slot placement, negation-form
coverage, unknown exemption consistency, teach follow-up count,
forget subtype/length consistency, the exact abstract-value DOMAIN of
every abstract slot (color/age/size/count/taste/occupation only;
occupation only on person hosts, taste only on food hosts), and the
author allocation matrix (exactly 5 items per author per category,
2 short/2 medium/1 long each, all 3 registers each, and every
multi-item subtype / construction / marker / form bin split between
authors as evenly as its count permits) plus set-wide author balance
on entity types (exactly 7/7 of each), registers (differ by at most
1 per register) and abstract domains (each multi-item domain split
as evenly as its total permits; singleton domains exempt), the
pronoun+decoy antecedent rule (a co-occurring decoy is
DISCOURSE-UNAVAILABLE at the pronoun, under EITHER safe ordering
(decoy not yet introduced at the pronoun, or introduced earlier,
explicitly closed and never reintroduced); the pronoun sits at most
one turn from its antecedent and the decoy appears in neither the
pronoun's turn nor the turn before; class distance is only a margin,
never the guarantee; unknown S05/S09 keep the pronoun in a setup
turn - on S09 before the trap fact appears - and their probes name
the subject), missing-referent item
definitions (0 setup facts, no candidate referent), person-kind
value domains disjoint from occupation, exact trap-marker matching,
and bin-list consistency (AUDIT_BINS / AUTHOR_SPLIT_BINS against
bins derived from ROWS). --verify-plan PATH diffs the emitted tables
against a plan document's section 4.8 and checks canonical bytes
(UTF-8, no BOM, LF, final newline, Thai in NFC) of both files.

This script's own sha256 goes into the freeze attestation next to the
plan's hash (spec v2.5 section 6.1). AI-authored / not human-validated.
"""
import hashlib
import re
import sys
import unicodedata
from collections import Counter

CATEGORIES = ["recall", "unknown", "contradiction", "ambiguity",
              "teach", "forget", "correction"]

LENGTH = ["short", "short", "short", "short",
          "medium", "medium", "medium", "medium", "long", "long"]
# Per-category register assignment (4/3/3 per category), chosen by
# exhaustive search so that every multi-item audit bin spans >=2
# registers within its category AND every slot sees all 3 registers
# across the set (section 5 audit rule is achievable by construction).
REGISTER = {
    "recall": ["khrup", "plain", "plain", "plain", "kha", "khrup", "khrup", "kha", "kha", "plain"],
    "unknown": ["khrup", "kha", "plain", "khrup", "plain", "kha", "khrup", "kha", "plain", "plain"],
    "contradiction": ["khrup", "kha", "plain", "khrup", "kha", "plain", "khrup", "plain", "plain", "kha"],
    "ambiguity": ["kha", "khrup", "kha", "kha", "plain", "plain", "plain", "khrup", "khrup", "plain"],
    "teach": ["plain", "kha", "plain", "kha", "plain", "khrup", "kha", "khrup", "plain", "khrup"],
    "forget": ["kha", "kha", "khrup", "khrup", "plain", "plain", "kha", "plain", "plain", "khrup"],
    "correction": ["plain", "khrup", "plain", "plain", "khrup", "khrup", "plain", "kha", "kha", "kha"],
}
# Register audit bins per category (name, 1-based slots); bins with
# >=2 items MUST span >=2 registers. Singletons are reported
# descriptively only (section 5).
AUDIT_BINS = {
    "recall": [("kind", [1, 5, 9]), ("attribute", [2, 6, 10]), ("location", [3, 7]), ("possession", [4, 8])],
    "unknown": [("untaught-relation", [1, 5, 7, 8, 9]), ("untaught-subject", [2, 6, 10]), ("missing-referent", [3, 4]),
                ("kind", [1, 6]), ("attribute", [2, 5, 10]), ("location", [3, 8]), ("possession", [4, 9])],
    "contradiction": [("kind", [1, 5, 9]), ("attribute", [2, 6, 10]), ("location", [3, 7]), ("possession", [4, 8]),
                      ("declarative", [1, 2, 3, 4, 5, 6, 9]), ("question", [7, 8, 10]), ("negated-ไม่ใช่", [5, 9])],
    "ambiguity": [("polysemy-homograph", [1, 2, 3, 4]), ("same-name", [5, 6, 9]), ("pronoun-2-antecedent", [7, 8, 10]),
                  ("attribute", [1, 3, 6, 9]), ("kind", [2, 5, 10]), ("location", [4, 8])],
    "teach": [("copula-เป็น", [1, 4, 5, 8]), ("copula-คือ", [6, 9]), ("possession-มี", [2, 3]),
              ("kind", [1, 4, 5, 8]), ("identify", [6, 9]), ("possession", [2, 3]),
              ("follow-up-probe", [5, 7, 8, 9, 10])],
    "forget": [("single-fact", [1, 2, 3, 4]), ("one-of-several", [5, 6, 7, 8, 9, 10]),
               ("ลบ...ออก", [1, 5, 9, 10]), ("อย่าจำ", [2, 6]), ("ไม่ต้องจำ...แล้ว", [3, 7]), ("ช่วยลบ...ออกหน่อย", [4, 8]),
               ("kind", [1, 5, 9]), ("attribute", [2, 6, 10]), ("location", [3, 7]), ("possession", [4, 8]),
               ("re-ask-probe", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])],
    "correction": [("ขอแก้ไขข้อมูลเดิม:", [1, 5, 10]), ("bare-แก้ไข", [2, 9]), ("เปลี่ยน", [3, 8]),
                   ("kind", [1, 4, 10]), ("attribute", [2, 3, 8]), ("location", [5, 7]), ("possession", [6, 9]),
                   ("post-correction-probe", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])],
}
# 5 entity types, exactly 2 slots each (S01-S10)
ENTITIES = ["person", "animal", "place", "object", "food",
            "person", "animal", "place", "object", "food"]

COMPAT = {
    "person": {"kind", "identify", "attribute", "location", "possession", "action"},
    "animal": {"kind", "identify", "attribute", "location", "possession", "action"},
    "place": {"kind", "identify", "attribute", "location", "possession"},
    "object": {"kind", "identify", "attribute", "location", "possession"},
    "food": {"kind", "identify", "attribute", "location"},
}
ABSTRACT_SHAPES = {"attribute", "kind", "identify"}

# rows: (subtype, shape, pronoun, decoy, abstract_value, note)
ROWS = {
    "recall": [
        ("kind", "kind", False, False, False, "adjacent probe; person-kind value from role/relationship/nationality (not occupation)"),
        ("attribute", "attribute", False, False, True, "adjacent probe; abstract value (color)"),
        ("location", "location", False, False, False, "adjacent probe"),
        ("possession", "possession", False, False, False, "adjacent probe"),
        ("kind", "kind", True, True, False, "intervening 2-3 turns; pronoun probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)"),
        ("attribute", "attribute", False, True, True, "adjacent probe; abstract value (size); decoy entity present"),
        ("location", "location", True, False, False, "intervening 2-3 turns; pronoun probe"),
        ("possession", "possession", False, True, False, "intervening 2-3 turns"),
        ("kind", "kind", True, False, False, "intervening 2-3 turns; pronoun probe"),
        ("attribute", "attribute", True, True, True, "intervening 2-3 turns; pronoun probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before); abstract value (taste)"),
    ],
    "unknown": [
        ("untaught-relation", "kind", False, False, False, "asked relation is NOT occupation (disjoint from the pinned occupation total)"),
        ("untaught-subject", "attribute", False, False, True, "abstract value (color)"),
        ("missing-referent", "location", True, False, False, "EXEMPT: zero-antecedent pronoun probe on a short slot; no trap; 0 setup facts, so the probe's มัน has NO candidate referent; the Entity column names the implied class of the non-existent referent"),
        ("missing-referent", "possession", True, False, False, "EXEMPT: zero-antecedent pronoun probe on a short slot; no trap; 0 setup facts, so the probe's มัน has NO candidate referent; the Entity column names the implied class of the non-existent referent"),
        ("untaught-relation", "attribute", True, True, True, "trap BEFORE the target facts, closed before the target's introduction; pronoun in a SETUP turn whose only subject is the target (the probe names the subject); decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before); abstract value (taste)"),
        ("untaught-subject", "kind", False, False, False, "asked relation is NOT occupation (disjoint from the pinned occupation total)"),
        ("untaught-relation", "action", False, True, False, "trap AFTER the target facts"),
        ("untaught-relation", "location", False, True, False, "trap BEFORE the target facts"),
        ("untaught-relation", "possession", True, True, False, "pronoun in a SETUP turn BEFORE the trap fact appears, its only subject the target (the probe names the subject); trap AFTER the target facts; decoy: person, discourse-unavailable at the pronoun (not yet introduced at the pronoun; pronoun at most one turn from the antecedent)"),
        ("untaught-subject", "attribute", False, False, True, "abstract value (taste: spiciness)"),
    ],
    "contradiction": [
        ("kind", "kind", False, False, False, "declarative, positive-conflict; person-kind value from role/relationship/nationality (not occupation)"),
        ("attribute", "attribute", False, False, True, "declarative, positive-conflict; abstract value (color)"),
        ("location", "location", False, False, False, "declarative, positive-conflict"),
        ("possession", "possession", False, False, False, "declarative, positive-conflict"),
        ("kind", "kind", True, True, False, "declarative, negated (ไม่ใช่); pronoun in assertion; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)"),
        ("attribute", "attribute", False, True, True, "declarative, positive-conflict; abstract value (age)"),
        ("location", "location", True, False, False, "question (ไม่ได้อยู่...หรือ); pronoun in assertion"),
        ("possession", "possession", False, True, False, "question (ไม่มี...ใช่ไหม)"),
        ("kind", "kind", True, False, False, "declarative, negated (ไม่ใช่); pronoun in assertion"),
        ("attribute", "attribute", True, True, True, "question (...ใช่ไหม), positive; pronoun in assertion; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before); abstract value (taste)"),
    ],
    "ambiguity": [
        ("polysemy-homograph", "attribute", False, False, True, "short-feasible; both readings identifiable from setup+probe (clause 4); abstract value (color)"),
        ("polysemy-homograph", "kind", False, False, False, "both readings identifiable from setup+probe"),
        ("polysemy-homograph", "attribute", False, False, True, "both readings identifiable; abstract value (age)"),
        ("polysemy-homograph", "location", False, False, False, "both readings identifiable"),
        ("same-name", "kind", False, True, False, "two referents inherent (counts as decoy item)"),
        ("same-name", "attribute", False, True, True, "two referents inherent; abstract value (occupation)"),
        ("pronoun-2-antecedent", "action", True, True, False, "FORCED anaphora; two animal antecedents (มัน), same animacy+number; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)"),
        ("pronoun-2-antecedent", "location", True, False, False, "FORCED anaphora; two place antecedents (มัน, extended inventory)"),
        ("same-name", "attribute", True, True, True, "pronoun probe over the two named referents (the same-name pair are the intended two มัน candidates); any additional decoy: person, discourse-unavailable at the pronoun (taught and closed before the referents' introduction, never re-mentioned; pronoun at most one turn from the antecedent pair; decoy absent from the pronoun's turn and the turn before); abstract value (size)"),
        ("pronoun-2-antecedent", "kind", True, False, False, "FORCED anaphora; two food antecedents (มัน)"),
    ],
    "teach": [
        ("copula-เป็น", "kind", False, False, False, "short: 0 setup facts; scored = instruction; person-kind value from role/relationship/nationality (not occupation)"),
        ("possession-มี", "possession", False, False, False, "short: 0 setup facts; count with classifier"),
        ("possession-มี", "possession", False, False, False, "short: 0 setup facts"),
        ("copula-เป็น", "kind", False, False, False, "short: 0 setup facts"),
        ("copula-เป็น", "kind", True, True, False, "follow-up recall probe (scored); pronoun probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)"),
        ("copula-คือ", "identify", False, True, True, "identifying Y; occupation (abstract value); decoy fact in setup, never probed (G-AX7 note)"),
        ("action-ability", "action", True, False, False, "follow-up recall probe (scored); pronoun probe"),
        ("copula-เป็น", "kind", False, True, False, "follow-up recall probe (scored)"),
        ("copula-คือ", "identify", True, True, False, "follow-up recall probe (scored); pronoun probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)"),
        ("location-อยู่ที่", "location", True, False, False, "follow-up recall probe (scored); pronoun probe"),
    ],
    "forget": [
        ("single-fact", "kind", False, False, False, "request-construction bin ลบ...ออก; universal re-ask probe; person-kind value from role/relationship/nationality (not occupation)"),
        ("single-fact", "attribute", False, False, True, "bin อย่าจำ; abstract value (color); universal re-ask"),
        ("single-fact", "location", False, False, False, "bin ไม่ต้องจำ...แล้ว; universal re-ask"),
        ("single-fact", "possession", False, False, False, "bin ช่วยลบ...ออกหน่อย; universal re-ask"),
        ("one-of-several", "kind", True, True, False, "bin ลบ...ออก; decoy entity present, its fact NEVER probed; other facts on the target subject; unrelated-fact probe asks one of THOSE; pronoun re-ask; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)"),
        ("one-of-several", "attribute", False, False, True, "bin อย่าจำ; other facts on the target subject; unrelated-fact probe asks one of them; abstract value (age)"),
        ("one-of-several", "location", True, False, False, "bin ไม่ต้องจำ...แล้ว; other facts on the target subject; unrelated-fact probe asks one of them; pronoun re-ask"),
        ("one-of-several", "possession", False, True, False, "bin ช่วยลบ...ออกหน่อย; decoy entity present, its fact NEVER probed; other facts on the target subject; unrelated-fact probe asks one of THOSE"),
        ("one-of-several", "kind", True, True, False, "bin ลบ...ออก; decoy entity present, its fact NEVER probed; other facts on the target subject; unrelated-fact probe asks one of THOSE; pronoun re-ask; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)"),
        ("one-of-several", "attribute", True, True, True, "bin ลบ...ออก; decoy entity present, its fact NEVER probed; other facts on the target subject; unrelated-fact probe asks one of THOSE; abstract value (taste); pronoun re-ask; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)"),
    ],
    "correction": [
        ("marker-ขอแก้ไขข้อมูลเดิม:", "kind", False, False, False, "post-correction probe (scored); person-kind value from role/relationship/nationality (not occupation)"),
        ("marker-แก้ไข:(bare)", "attribute", False, False, True, "abstract value (color); post-correction probe"),
        ("marker-เปลี่ยน X เป็น Y", "attribute", False, False, True, "abstract value (size); post-correction probe"),
        ("marker-ไม่ใช่ X แต่เป็น Y", "kind", False, False, False, "negation form ไม่ใช่; post-correction probe"),
        ("marker-ขอแก้ไขข้อมูลเดิม:", "location", True, True, False, "pronoun in post-correction probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)"),
        ("marker-ไม่มี X แต่มี Y", "possession", False, True, False, "negation form ไม่มี; post-correction probe"),
        ("marker-ไม่ได้อยู่ X แต่อยู่ Y", "location", True, False, False, "negation form ไม่ได้+verb; pronoun probe"),
        ("marker-เปลี่ยน X เป็น Y", "attribute", False, True, True, "abstract value (count); post-correction probe"),
        ("marker-แก้ไข:(bare)", "possession", True, True, False, "pronoun in post-correction probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)"),
        ("marker-ขอแก้ไขข้อมูลเดิม:", "kind", True, False, False, "pronoun in post-correction probe"),
    ],
}

PRON_EXEMPT = {"unknown": {3, 4}}  # 1-based slots, zero-antecedent probes

# Pinned expected defensible-antecedent counts per pronoun slot
# (section 6 rule 8 / section 5 spot audit): 0 on the missing-referent
# exemptions, 2 on ambiguity's four pronoun slots (S07/S08/S10
# pronoun-2-antecedent, S09 same-name with two intended candidates),
# 1 everywhere else.
def expected_antecedents(cat, i):
    st = ROWS[cat][i][0]
    if st == "missing-referent":
        return 0
    if cat == "ambiguity":
        return 2
    return 1

# Pinned pronoun+decoy intersection (15 slots; section 5 spot audit).
# forget S09 is the 15th: pronoun AND decoy are both set on it.
PRONOUN_DECOY = {
    "recall": [5, 10], "unknown": [5, 9], "contradiction": [5, 10],
    "ambiguity": [7, 9], "teach": [5, 9], "forget": [5, 9, 10],
    "correction": [5, 9],
}

# Author allocation matrix (v6, GPT v5 B1): slots authored by family
# A; family B authors the rest. Chosen by exhaustive search so that
# each family authors exactly 5 items per category with 2 short / 2
# medium / 1 long, sees all 3 registers per category, splits every
# multi-item bin in AUTHOR_SPLIT_BINS as evenly as its count permits
# (singleton bins exempt), AND balances set-wide: each entity type
# exactly 7/7, registers differing by at most 1 per register
# (plain 14/14, khrup 11/10, kha 10/11), and every multi-item
# abstract domain split as evenly as its total permits (color 3/3,
# taste 2/3, age 1/2, size 1/2, occupation 1/1; singleton count
# exempt).
AUTHOR = {
    "recall":        ["A", "A", "B", "B", "B", "B", "A", "A", "A", "B"],
    "unknown":       ["A", "B", "A", "B", "A", "A", "B", "B", "A", "B"],
    "contradiction": ["A", "A", "B", "B", "B", "B", "A", "A", "A", "B"],
    "ambiguity":     ["B", "B", "A", "A", "A", "B", "A", "B", "A", "B"],
    "teach":         ["A", "A", "B", "B", "A", "A", "B", "B", "B", "A"],
    "forget":        ["B", "A", "A", "B", "A", "B", "B", "A", "B", "A"],
    "correction":    ["A", "B", "B", "A", "A", "B", "B", "A", "A", "B"],
}
# Multi-item bins that must be split between authors as evenly as
# their count permits: subtype roots plus contradiction's
# declarative/question forms, teach's copula/possession
# constructions, forget's request constructions and correction's
# multi-item markers (subtype roots already cover them).
AUTHOR_SPLIT_BINS = {
    "recall": [("kind", [1, 5, 9]), ("attribute", [2, 6, 10]), ("location", [3, 7]), ("possession", [4, 8])],
    "unknown": [("untaught-relation", [1, 5, 7, 8, 9]), ("untaught-subject", [2, 6, 10]), ("missing-referent", [3, 4])],
    "contradiction": [("kind", [1, 5, 9]), ("attribute", [2, 6, 10]), ("location", [3, 7]), ("possession", [4, 8]),
                      ("declarative", [1, 2, 3, 4, 5, 6, 9]), ("question", [7, 8, 10])],
    "ambiguity": [("polysemy-homograph", [1, 2, 3, 4]), ("same-name", [5, 6, 9]), ("pronoun-2-antecedent", [7, 8, 10])],
    "teach": [("copula-เป็น", [1, 4, 5, 8]), ("copula-คือ", [6, 9]), ("possession-มี", [2, 3])],
    "forget": [("single-fact", [1, 2, 3, 4]), ("one-of-several", [5, 6, 7, 8, 9, 10]),
               ("ลบ...ออก", [1, 5, 9, 10]), ("อย่าจำ", [2, 6]), ("ไม่ต้องจำ...แล้ว", [3, 7]), ("ช่วยลบ...ออกหน่อย", [4, 8])],
    "correction": [("ขอแก้ไขข้อมูลเดิม:", [1, 5, 10]), ("แก้ไข:(bare)", [2, 9]), ("เปลี่ยน", [3, 8])],
}
# Exact abstract-value domain per abstract slot (v5, GPT B2 + N1).
# Authoritative domain list (G-AX3b): color, age, size, count, taste
# (spiciness is a taste value), occupation (person hosts only). Keys
# must equal exactly the rows with abstract_value=True.
ABSTRACT_DOMAIN = {
    "recall": {2: "color", 6: "size", 10: "taste"},
    "unknown": {2: "color", 5: "taste", 10: "taste (spiciness)"},
    "contradiction": {2: "color", 6: "age", 10: "taste"},
    "ambiguity": {1: "color", 3: "age", 6: "occupation", 9: "size"},
    "teach": {6: "occupation"},
    "forget": {2: "color", 6: "age", 10: "taste"},
    "correction": {2: "color", 3: "size", 8: "count"},
}
DOMAIN_LIST = {"color", "age", "size", "count", "taste", "occupation"}
# Set-wide abstract domain totals (pinned; coverage reporting).
DOMAIN_TOTALS = {"color": 6, "taste": 5, "age": 3, "size": 3, "occupation": 2, "count": 1}

SCORED = {
    "recall": "every probe turn: {supported, answer}",
    "unknown": "the probe turn (instruction-under-test): {unknown, abstain}",
    "contradiction": "the agent's reply WITHIN the same turn as the conflicting assertion (the instruction-under-test): {contradicted, answer}. No separate follow-up turn exists in this category.",
    "ambiguity": "the ambiguous probe turn: {ambiguous, clarify}",
    "teach": "instruction turn: {supported, acknowledge}; exactly 5 items (S05, S07-S10) add one follow-up recall probe: {supported, answer}",
    "forget": "instruction turn: {unknown, acknowledge}; universal final re-ask probe: {unknown, abstain}; one-of-several items add an unrelated-fact recall probe: {supported, answer}",
    "correction": "instruction turn: {supported, acknowledge}; universal post-correction probe: {supported, answer}",
}

EXP = {
    "recall": {"kind": 3, "attribute": 3, "location": 2, "possession": 2},
    "unknown": {"untaught-relation": 5, "untaught-subject": 3, "missing-referent": 2},
    "contradiction": {"kind": 3, "attribute": 3, "location": 2, "possession": 2},
    "ambiguity": {"polysemy-homograph": 4, "same-name": 3, "pronoun-2-antecedent": 3},
    "teach": {"copula-เป็น": 4, "copula-คือ": 2, "possession-มี": 2, "location-อยู่ที่": 1, "action-ability": 1},
    "forget": {"single-fact": 4, "one-of-several": 6},
    "correction": {"marker-ขอแก้ไขข้อมูลเดิม:": 3, "marker-แก้ไข:(bare)": 2, "marker-เปลี่ยน X เป็น Y": 2,
                   "marker-ไม่ใช่ X แต่เป็น Y": 1, "marker-ไม่มี X แต่มี Y": 1, "marker-ไม่ได้อยู่ X แต่อยู่ Y": 1},
}


def check():
    errs = []
    for cat in CATEGORIES:
        rows = ROWS[cat]
        assert len(rows) == 10
        if LENGTH.count("short") != 4 or LENGTH.count("medium") != 4 or LENGTH.count("long") != 2:
            errs.append(f"{cat}: length skeleton != 4/4/2")
        reg = REGISTER[cat]
        if reg.count("plain") != 4 or reg.count("khrup") != 3 or reg.count("kha") != 3:
            errs.append(f"{cat}: register != 4/3/3")
        # register audit achievability (section 5): every multi-item
        # audit bin spans >=2 registers within its category
        for name, slots in AUDIT_BINS[cat]:
            if len(slots) >= 2 and len({reg[s - 1] for s in slots}) < 2:
                errs.append(f"{cat}: audit bin {name} confined to one register")
        # pronoun exactly 4; medium/long unless exempt
        pr = [i + 1 for i in range(10) if rows[i][2]]
        if len(pr) != 4:
            errs.append(f"{cat}: pronoun count {len(pr)} != 4")
        for s in pr:
            if LENGTH[s - 1] == "short" and s not in PRON_EXEMPT.get(cat, set()):
                errs.append(f"{cat}: pronoun on short slot S{s:02d} without exemption")
        # decoy exactly 4, never on a short slot (a decoy carries its
        # own taught setup fact; short allows at most 1)
        dc = [i + 1 for i in range(10) if rows[i][3]]
        if len(dc) != 4:
            errs.append(f"{cat}: decoy count {len(dc)} != 4")
        for s in dc:
            if LENGTH[s - 1] == "short":
                errs.append(f"{cat}: INFEASIBLE decoy on short slot S{s:02d}")
        # entity types: 5 bins, exactly 2 each
        ec = Counter(ENTITIES)
        if sorted(ec.values()) != [2, 2, 2, 2, 2]:
            errs.append(f"{cat}: entity types not exactly 2 each: {dict(ec)}")
        # value domains: 1-4 abstract-valued; abstract only with
        # attribute/kind/identify shapes; occupation only on person hosts
        ab = [i + 1 for i in range(10) if rows[i][4]]
        if not (1 <= len(ab) <= 4):
            errs.append(f"{cat}: abstract-valued count {len(ab)} outside 1-4")
        for s in ab:
            if rows[s - 1][1] not in ABSTRACT_SHAPES:
                errs.append(f"{cat}: S{s:02d} abstract value with shape {rows[s-1][1]}")
            if "occupation" in rows[s - 1][5] and ENTITIES[s - 1] != "person":
                errs.append(f"{cat}: S{s:02d} occupation value on non-person host")
        # shapes: >=3 distinct, max 5; compat with entity
        sc = Counter(r[1] for r in rows)
        if len(sc) < 3:
            errs.append(f"{cat}: fewer than 3 shapes")
        if max(sc.values()) > 5:
            errs.append(f"{cat}: shape dominates ({max(sc.values())})")
        for i in range(10):
            if rows[i][1] not in COMPAT[ENTITIES[i]]:
                errs.append(f"{cat}: S{i+1:02d} shape {rows[i][1]} incompatible with {ENTITIES[i]}")
        # subtype partition
        if dict(Counter(r[0] for r in rows)) != EXP[cat]:
            errs.append(f"{cat}: subtype counts != pinned")
        # abstract domains: pinned per slot, authoritative list,
        # host rules, note consistency
        ad = ABSTRACT_DOMAIN[cat]
        if set(ad) != set(ab):
            errs.append(f"{cat}: abstract domain slots {sorted(ad)} != abstract rows {ab}")
        for s, dom in ad.items():
            base = dom.split(" ")[0]
            if base not in DOMAIN_LIST:
                errs.append(f"{cat}: S{s:02d} domain {dom} not in authoritative list")
            if base == "taste" and ENTITIES[s - 1] != "food":
                errs.append(f"{cat}: S{s:02d} taste value on non-food host")
            if base not in rows[s - 1][5] and base != "taste":
                errs.append(f"{cat}: S{s:02d} note does not name domain {dom}")
        # author allocation matrix (v5)
        au = AUTHOR[cat]
        for fam in "AB":
            idx = [i for i in range(10) if au[i] == fam]
            if len(idx) != 5:
                errs.append(f"{cat}: author {fam} has {len(idx)} != 5 items")
            lc = Counter(LENGTH[i] for i in idx)
            if (lc["short"], lc["medium"], lc["long"]) != (2, 2, 1):
                errs.append(f"{cat}: author {fam} lengths {dict(lc)} != 2/2/1")
            if len({reg[i] for i in idx}) < 3:
                errs.append(f"{cat}: author {fam} misses a register")
        for name, slots in AUTHOR_SPLIT_BINS[cat]:
            c = len(slots)
            a = sum(1 for s in slots if au[s - 1] == "A")
            if abs(a - (c - a)) > (c % 2):
                errs.append(f"{cat}: author split of {name} ({a}/{c - a}) not even")
    # set-wide register diversity: every slot sees all 3 registers
    # across the seven categories (the prose pins all 3)
    for i in range(10):
        seen = {REGISTER[c][i] for c in CATEGORIES}
        if len(seen) < 3:
            errs.append(f"slot S{i+1:02d}: only {sorted(seen)} across the set")
    # cross-category multi-item bins: action shape sits on S07 in
    # unknown/ambiguity/teach and must span >=2 registers set-wide
    a7 = {REGISTER[c][6] for c in ["unknown", "ambiguity", "teach"]}
    if len(a7) < 2:
        errs.append("action shape (S07 x3 categories) confined to one register set-wide")
    # set-wide author balance (v6, GPT v5 B1 + non-blockings): entity
    # types exactly 7/7; registers differ by at most 1; each
    # multi-item abstract domain split as evenly as its total permits
    ea = Counter(ENTITIES[i] for c in CATEGORIES for i in range(10) if AUTHOR[c][i] == "A")
    if any(ea[e] != 7 for e in set(ENTITIES)):
        errs.append(f"author entity balance {dict(ea)} != 7/7 each")
    ra = Counter(REGISTER[c][i] for c in CATEGORIES for i in range(10) if AUTHOR[c][i] == "A")
    for r, total in (("plain", 28), ("khrup", 21), ("kha", 21)):
        if abs(2 * ra[r] - total) > (total % 2):
            errs.append(f"author register balance for {r}: {ra[r]}/{total - ra[r]} not even")
    da = Counter(ABSTRACT_DOMAIN[c][s].split(" ")[0]
                 for c in CATEGORIES for s in ABSTRACT_DOMAIN[c] if AUTHOR[c][s - 1] == "A")
    for d, total in DOMAIN_TOTALS.items():
        if abs(2 * da.get(d, 0) - total) > (total % 2):
            errs.append(f"author domain balance for {d}: {da.get(d, 0)}/{total - da.get(d, 0)} not even")
    # set-wide abstract domain totals (pinned for coverage reporting)
    tot = Counter(d.split(" ")[0] for c in CATEGORIES for d in ABSTRACT_DOMAIN[c].values())
    if dict(tot) != DOMAIN_TOTALS:
        errs.append(f"abstract domain totals {dict(tot)} != pinned {DOMAIN_TOTALS}")
    # unknown trap positions: exact markers, at least one BEFORE and
    # one AFTER, and trap markers exactly on the decoy slots
    tb = {i + 1 for i in range(10) if "trap BEFORE" in ROWS["unknown"][i][5]}
    ta = {i + 1 for i in range(10) if "trap AFTER" in ROWS["unknown"][i][5]}
    if not tb or not ta:
        errs.append("unknown: trap positions lack BEFORE/AFTER spread")
    if tb | ta != {i + 1 for i in range(10) if ROWS["unknown"][i][3]}:
        errs.append("unknown: trap markers not exactly on the decoy slots")
    # forget decoy slots: the unrelated-fact probe never asks the decoy fact
    for i in range(10):
        r = ROWS["forget"][i]
        if r[3] and "NEVER probed" not in r[5]:
            errs.append(f"forget S{i+1:02d}: decoy note missing probe-target rule")
    # pronoun+decoy intersection equals the pinned 15 slots
    for cat in CATEGORIES:
        derived = [i + 1 for i in range(10) if ROWS[cat][i][2] and ROWS[cat][i][3]]
        if derived != PRONOUN_DECOY[cat]:
            errs.append(f"{cat}: pronoun+decoy slots {derived} != pinned {PRONOUN_DECOY[cat]}")
    if sum(len(v) for v in PRONOUN_DECOY.values()) != 15:
        errs.append("pronoun+decoy pinned total != 15")
    # set-wide pronoun slots total 28 (4 per category x 7; section 5)
    if sum(1 for c in CATEGORIES for i in range(10) if ROWS[c][i][2]) != 28:
        errs.append("set-wide pronoun slot total != 28")
    # pronoun+decoy co-occurrence (Claude B1, GPT v7 B1): the decoy
    # is discourse-unavailable at the pronoun (the binding rule);
    # the pinned person decoy is only an extra class-distance margin
    for cat in CATEGORIES:
        for i in range(10):
            st, sh, pr, dc, ab, note = ROWS[cat][i]
            m = re.search(r"decoy: (person|animal|place|object|food)", note)
            if pr and dc:
                if "discourse-unavailable" not in note:
                    errs.append(f"{cat} S{i+1:02d}: pronoun+decoy without the discourse-unavailability pin")
                if "at most one turn from the antecedent" not in note:
                    errs.append(f"{cat} S{i+1:02d}: pronoun+decoy without the antecedent-adjacency pin")
                if not m:
                    errs.append(f"{cat} S{i+1:02d}: pronoun+decoy without a declared decoy class")
                elif (m.group(1) == "person") == (ENTITIES[i] == "person"):
                    errs.append(f"{cat} S{i+1:02d}: decoy class margin broken (not person vs non-person host)")
            elif m and not dc:
                errs.append(f"{cat} S{i+1:02d}: decoy note on a non-decoy slot")
    # unknown S05/S09: pronoun in a setup turn, probe names the subject
    for s in (5, 9):
        note = ROWS["unknown"][s - 1][5]
        if "SETUP turn" not in note or "pronoun probe" in note:
            errs.append(f"unknown S{s:02d}: pronoun not moved to a setup turn")
    if "BEFORE the trap fact" not in ROWS["unknown"][8][5]:
        errs.append("unknown S09: pronoun not pinned before the trap fact appears")
    # missing-referent items: 0 setup facts, no candidate referent
    for s in (3, 4):
        if "0 setup facts" not in ROWS["unknown"][s - 1][5]:
            errs.append(f"unknown S{s:02d}: missing-referent definition missing")
    # person-host kind values disjoint from occupation
    for cat in CATEGORIES:
        for i in range(10):
            if ENTITIES[i] == "person" and ROWS[cat][i][1] == "kind":
                note = ROWS[cat][i][5]
                if cat == "unknown":
                    if "NOT occupation" not in note:
                        errs.append(f"unknown S{i+1:02d}: person-kind probe not disjoint from occupation")
                elif "role/relationship/nationality" not in note:
                    errs.append(f"{cat} S{i+1:02d}: person-kind value domain not pinned")
    # bin lists match bins derived from ROWS (no silent drift)
    for cat in CATEGORIES:
        audit_sets = {tuple(sorted(sl)) for _, sl in AUDIT_BINS[cat]}
        split_sets = {tuple(sorted(sl)) for _, sl in AUTHOR_SPLIT_BINS[cat]}
        derived = {}
        for i, r in enumerate(ROWS[cat]):
            derived.setdefault(("subtype", r[0]), []).append(i + 1)
            derived.setdefault(("shape", r[1]), []).append(i + 1)
        for (kind, name), sl in sorted(derived.items()):
            if len(sl) < 2:
                continue
            if tuple(sorted(sl)) not in audit_sets:
                errs.append(f"{cat}: derived {kind} bin {name} {sl} missing from AUDIT_BINS")
            if kind == "subtype" and tuple(sorted(sl)) not in split_sets:
                errs.append(f"{cat}: derived subtype bin {name} {sl} missing from AUTHOR_SPLIT_BINS")
    # antecedent-count table: every pronoun slot's expectation follows
    # the pinned mapping (0 missing-referent, 2 ambiguity, 1 else)
    for cat in CATEGORIES:
        for i in range(10):
            if not ROWS[cat][i][2]:
                continue
            st = ROWS[cat][i][0]
            exp = 0 if st == "missing-referent" else (2 if cat == "ambiguity" else 1)
            if exp != expected_antecedents(cat, i):
                errs.append(f"{cat} S{i+1:02d}: antecedent expectation drifted from the pinned table")
    # unknown exemptions: short, missing-referent, pronoun, no decoy
    for s in PRON_EXEMPT["unknown"]:
        r = ROWS["unknown"][s - 1]
        if LENGTH[s - 1] != "short" or r[0] != "missing-referent" or not r[2] or r[3]:
            errs.append(f"unknown: exemption slot S{s:02d} inconsistent")
    # ambiguity: polysemy exactly the short slots; pronoun-2-antecedent
    # slots all carry pronoun=True
    for i in range(10):
        st = ROWS["ambiguity"][i][0]
        if st == "polysemy-homograph" and LENGTH[i] != "short":
            errs.append(f"ambiguity: polysemy on non-short S{i+1:02d}")
        if st == "pronoun-2-antecedent" and not ROWS["ambiguity"][i][2]:
            errs.append(f"ambiguity: pronoun subtype without pronoun on S{i+1:02d}")
    # teach: exactly 5 follow-up probes, all medium/long
    fu = [i + 1 for i in range(10) if "follow-up" in ROWS["teach"][i][5]]
    if fu != [5, 7, 8, 9, 10]:
        errs.append(f"teach: follow-up probes on {fu} != [5,7,8,9,10]")
    # forget: single-fact short, one-of-several medium/long
    for i in range(10):
        st = ROWS["forget"][i][0]
        if st == "single-fact" and LENGTH[i] != "short":
            errs.append(f"forget: single-fact on non-short S{i+1:02d}")
        if st == "one-of-several" and LENGTH[i] == "short":
            errs.append(f"forget: one-of-several on short S{i+1:02d}")
    # negation coverage
    neg = {"ไม่ใช่", "ไม่มี", "ไม่ได้"}
    found = {f for r in ROWS["contradiction"] for f in neg if f in r[5]}
    if len(found) < 2:
        errs.append(f"contradiction: negation forms {found} < 2")
    cf = {f for r in ROWS["correction"] for f in neg if f in r[0]}
    if cf != {"ไม่ใช่", "ไม่มี", "ไม่ได้"}:
        errs.append(f"correction: negation forms {cf} != 3 required")
    return errs


def emit():
    out = []
    for cat in CATEGORIES:
        out.append(f"#### {cat} slot table\n")
        out.append("| Slot | Author | Length | Register | Entity | Subtype | Shape | Abstract value | Pronoun | Decoy | Scored turns / notes |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for i in range(10):
            st, sh, pr, dc, ab, note = ROWS[cat][i]
            dom = ABSTRACT_DOMAIN[cat].get(i + 1, "no")
            out.append(f"| S{i+1:02d} | {AUTHOR[cat][i]} | {LENGTH[i]} | {REGISTER[cat][i]} | {ENTITIES[i]} | {st} | {sh} | {dom if ab else 'no'} | {'yes' if pr else 'no'} | {'yes' if dc else 'no'} | {note} |")
        out.append(f"\nScored-turn rule: {SCORED[cat]}\n")
    return "\n".join(out)


if __name__ == "__main__":
    errors = check()
    if errors:
        print("CHECK FAILURES:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("ok all slot-table checks pass (7 categories x 10 slots)")
    if "--emit" in sys.argv:
        print(emit())
    if "--self-hash" in sys.argv:
        print("self sha256:", hashlib.sha256(open(__file__, "rb").read()).hexdigest())
    if "--verify-plan" in sys.argv:
        path = sys.argv[sys.argv.index("--verify-plan") + 1]
        def canonical(p):
            raw = open(p, "rb").read()
            if raw.startswith(b"\xef\xbb\xbf"):
                return "has a BOM"
            try:
                t = raw.decode("utf-8")
            except UnicodeDecodeError:
                return "not UTF-8"
            if "\r" in t:
                return "has CR line endings"
            if not t.endswith("\n"):
                return "no final newline"
            if unicodedata.normalize("NFC", t) != t:
                return "not NFC"
            return None
        bad = canonical(path) or canonical(__file__)
        if bad:
            print("verify-plan FAIL: canonical bytes:", bad)
            sys.exit(1)
        doc = open(path, encoding="utf-8").read()
        try:
            block = doc[doc.index("#### recall slot table"):doc.index("## 5. Scored-turn protocol")].strip()
        except ValueError:
            print("verify-plan FAIL: table block markers not found")
            sys.exit(1)
        if block != emit().strip():
            print("verify-plan FAIL: section 4.8 tables differ from --emit output")
            sys.exit(1)
        print("verify-plan ok: section 4.8 matches --emit; canonical bytes ok (plan + script)")
