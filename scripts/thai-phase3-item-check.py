#!/usr/bin/env python3
"""thai-core Phase 3 item validator: validates authored item JSON against
the pinned variation plan v12.1 (sections 1-10 + Annex A).

Structural checks only. Thai naturalness, semantic antecedent truth and
domain correctness are NOT established here - those rest on the author
self-check records, the Phase 6 audits, and the AI-authored /
not human-validated label. This script checks: family slot assignment
(exact 35, per the pinned Author matrix), register bins, forbidden
forms, pronoun presence/absence vs the flag, antecedent self-check
presence and pinned counts, scored-turn protocol per category, the
single-turn rules (teach short, missing-referent), forget request
constructions, correction markers, and the correction-marker ban in
contradiction.

AI-authored / not human-validated.
"""
import importlib.util
import json
import re
import sys

spec = importlib.util.spec_from_file_location(
    "slotcheck", "thai-phase2-slot-check.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

PRONOUNS = ["พวกเขา", "พวกมัน", "เขา", "มัน"]
FORBIDDEN = ["เธอ", "ช่วยลืม"]

EXPECTED_LABELS = {
    "recall": [["supported", "answer"]],
    "unknown": [["unknown", "abstain"]],
    "contradiction": [["contradicted", "answer"]],
    "ambiguity": [["ambiguous", "clarify"]],
    "teach": [["supported", "acknowledge"], ["supported", "answer"]],
    "forget": [["unknown", "acknowledge"], ["unknown", "abstain"], ["supported", "answer"]],
    "correction": [["supported", "acknowledge"], ["supported", "answer"]],
}

def expected_antecedents(cat, slot1):
    st = m.ROWS[cat][slot1 - 1][0]
    if st == "missing-referent":
        return 0
    if cat == "ambiguity":
        return 2
    return 1

def has_pronoun(text):
    return any(p in text for p in PRONOUNS)

def validate(path, family_letter, family_name):
    errs = []
    warns = []
    d = json.load(open(path, encoding="utf-8"))
    prov = d.get("provenance", {})
    if prov.get("method") != "ai-authored":
        errs.append("provenance.method != ai-authored")
    if "not human-validated" not in prov.get("label", ""):
        errs.append("provenance label missing 'not human-validated'")
    authors = prov.get("authors", [])
    if len(authors) != 1 or authors[0].get("family") != family_name:
        errs.append(f"provenance authors != one {family_name}-family author")
    items = d.get("items", [])
    seen = set()
    want = {f"{cat}-S{i+1:02d}" for cat in m.CATEGORIES
            for i in range(10) if m.AUTHOR[cat][i] == family_letter}
    for it in items:
        iid = it.get("id", "?")
        if iid in seen:
            errs.append(f"{iid}: duplicate")
        seen.add(iid)
        cat = it.get("category")
        slot = it.get("slot", "")
        if iid != f"{cat}-{slot}":
            errs.append(f"{iid}: id/category/slot mismatch")
            continue
        if cat not in m.CATEGORIES or not re.fullmatch(r"S\d\d", slot):
            errs.append(f"{iid}: bad category or slot")
            continue
        s = int(slot[1:])
        if cat not in m.CATEGORIES:
            continue
        if iid not in want:
            errs.append(f"{iid}: not assigned to family {family_letter} in the Author matrix")
            continue
        rows = m.ROWS[cat][s - 1]
        st, sh, pr, dc, ab, note = rows
        reg = m.REGISTER[cat][s - 1]
        turns = it.get("turns", [])
        if not turns or not all(isinstance(t, str) and t.strip() for t in turns):
            errs.append(f"{iid}: empty or non-string turns")
            continue
        alltext = "\n".join(turns)
        # register bin
        has_khrup = "ครับ" in alltext
        has_kha = ("ค่ะ" in alltext) or ("คะ" in alltext)
        if reg == "khrup" and (not has_khrup or has_kha):
            errs.append(f"{iid}: register khrup violated (khrup={has_khrup} kha={has_kha})")
        if reg == "kha" and (not has_kha or has_khrup):
            errs.append(f"{iid}: register kha violated (khrup={has_khrup} kha={has_kha})")
        if reg == "plain" and (has_khrup or has_kha):
            errs.append(f"{iid}: register plain violated (particles found)")
        if "ค่ะ?" in alltext:
            errs.append(f"{iid}: forbidden frame ...ค่ะ?")
        # forbidden forms
        for f in FORBIDDEN:
            if f in alltext:
                errs.append(f"{iid}: forbidden form {f}")
        # pronoun flag
        if pr:
            if not has_pronoun(alltext):
                errs.append(f"{iid}: pronoun slot without any pronoun form")
            asc = it.get("antecedent_self_check")
            if not asc:
                errs.append(f"{iid}: pronoun slot missing antecedent_self_check")
            else:
                exp = expected_antecedents(cat, s)
                for entry in asc:
                    c = entry.get("count")
                    da = entry.get("defensible_antecedents", [])
                    if c != exp:
                        errs.append(f"{iid}: self-check count {c} != pinned {exp}")
                    if c != len(da):
                        errs.append(f"{iid}: self-check count {c} != listed antecedents {len(da)}")
                    if not (1 <= entry.get("turn", 0) <= len(turns)):
                        errs.append(f"{iid}: self-check turn out of range")
        else:
            if has_pronoun(alltext):
                errs.append(f"{iid}: pronoun form on a non-pronoun slot")
        # pronoun slots medium/long unless exempt
        if pr and m.LENGTH[s - 1] == "short" and s not in m.PRON_EXEMPT.get(cat, set()):
            errs.append(f"{iid}: pronoun on short slot without exemption")
        # scored turns vs category protocol
        scored = it.get("scored_turns", [])
        if not scored:
            errs.append(f"{iid}: no scored turns")
        for scd in scored:
            t = scd.get("turn", 0)
            if not (1 <= t <= len(turns)):
                errs.append(f"{iid}: scored turn {t} out of range")
            if scd.get("expected") not in EXPECTED_LABELS[cat]:
                errs.append(f"{iid}: unexpected labels {scd.get('expected')}")
        exp_labels = [scd.get("expected") for scd in scored]
        if cat in ("recall", "unknown", "contradiction", "ambiguity"):
            want_n = 1 if cat != "recall" else None
            if want_n and len(scored) != want_n:
                errs.append(f"{iid}: {cat} must have exactly 1 scored turn, got {len(scored)}")
            if cat == "recall" and any(e != ["supported", "answer"] for e in exp_labels):
                errs.append(f"{iid}: recall scored labels wrong")
        if cat == "teach":
            if exp_labels[0] != ["supported", "acknowledge"]:
                errs.append(f"{iid}: teach instruction turn must be first scored")
            if s in (5, 7, 8, 9, 10):
                if len(scored) != 2 or exp_labels[1] != ["supported", "answer"]:
                    errs.append(f"{iid}: teach follow-up item must have 2 scored turns")
            else:
                if len(scored) != 1:
                    errs.append(f"{iid}: teach non-follow-up item must have 1 scored turn")
                if s in (1, 2, 3, 4) and len(turns) != 1:
                    errs.append(f"{iid}: teach short item must be a single turn")
                if s == 6 and len(turns) < 2:
                    errs.append(f"{iid}: teach S06 is medium with a decoy setup fact (needs >=2 turns)")
        if cat == "forget":
            if exp_labels[0] != ["unknown", "acknowledge"] or ["unknown", "abstain"] not in exp_labels:
                errs.append(f"{iid}: forget needs instruction + universal re-ask scored")
            if st == "one-of-several" and ["supported", "answer"] not in exp_labels:
                errs.append(f"{iid}: forget one-of-several needs the unrelated-fact probe scored")
            # request construction bin
            bins = {"ลบ...ออก": ["ลบ", "ออก"], "อย่าจำ": ["อย่าจำ"],
                    "ไม่ต้องจำ...แล้ว": ["ไม่ต้องจำ", "แล้ว"],
                    "ช่วยลบ...ออกหน่อย": ["ช่วยลบ", "ออก"]}
            bname = None
            for b in bins:
                if f"bin {b}" in note:
                    bname = b
            if bname and not all(x in alltext for x in bins[bname]):
                errs.append(f"{iid}: forget construction {bname} not found in turns")
        if cat == "correction":
            if exp_labels[0] != ["supported", "acknowledge"] or ["supported", "answer"] not in exp_labels:
                errs.append(f"{iid}: correction needs instruction + post-correction probe scored")
            marker = st.replace("marker-", "")
            key = {"ขอแก้ไขข้อมูลเดิม:": "ขอแก้ไขข้อมูลเดิม", "แก้ไข:(bare)": "แก้ไข",
                   "เปลี่ยน X เป็น Y": "เปลี่ยน", "ไม่ใช่ X แต่เป็น Y": "ไม่ใช่",
                   "ไม่มี X แต่มี Y": "ไม่มี", "ไม่ได้อยู่ X แต่อยู่ Y": "ไม่ได้อยู่"}[marker]
            if key not in alltext:
                errs.append(f"{iid}: correction marker {key} not found in turns")
        if cat == "contradiction" and "แต่เป็น" in alltext:
            errs.append(f"{iid}: correction marker ไม่ใช่ X แต่เป็น Y forbidden in contradiction")
        # single-turn rules
        if cat == "unknown" and st == "missing-referent":
            if len(turns) != 1:
                errs.append(f"{iid}: missing-referent item must have 0 setup facts (single turn)")
        # unknown S05/S09: probe names the subject (no pronoun in the scored probe turn)
        if cat == "unknown" and s in (5, 9):
            for scd in scored:
                if has_pronoun(turns[scd["turn"] - 1]):
                    errs.append(f"{iid}: unknown S{s:02d} probe turn must name the subject, not a pronoun")
        # abstract flag consistency (light): note-required domain presence is semantic; skipped
        # decoy on medium/long only (already guaranteed by skeleton, double-check)
        if dc and m.LENGTH[s - 1] == "short":
            errs.append(f"{iid}: decoy on a short slot")
        # soft: short items carry 0-1 setup facts, so at most one
        # non-scored setup turn is expected
        if m.LENGTH[s - 1] == "short" and len(turns) - len(scored) > 1:
            warns.append(f"{iid}: short item with {len(turns) - len(scored)} setup turns (0-1 setup facts expected)")
    missing = want - seen
    extra = seen - want
    if missing:
        errs.append(f"missing assigned items: {sorted(missing)}")
    if extra:
        errs.append(f"items not assigned to this family: {sorted(extra)}")
    if len(items) != 35:
        errs.append(f"item count {len(items)} != 35")
    return errs, warns

if __name__ == "__main__":
    path, fam_letter, fam_name = sys.argv[1], sys.argv[2], sys.argv[3]
    errs, warns = validate(path, fam_letter, fam_name)
    for w in warns:
        print("WARN:", w)
    if errs:
        print(f"FAIL {len(errs)} structural errors:")
        for e in errs:
            print(" -", e)
        sys.exit(1)
    print(f"ok {path}: 35 items structurally valid for family {fam_name} ({len(warns)} warnings)")
