#!/usr/bin/env python3
"""thai-derived-view: emit the checker-consumable DERIVED manifest for
thai-core-ai-v1 from the five frozen files (commit d800d43).

DERIVED AND NON-NORMATIVE. The canonical artifacts are the frozen five
files; this view exists so the in-agent thai-check (spec v2.5 AI path,
A' rollup per the 2026-11-27 section-4.4 clarification) can consume the
frozen set. It never mutates the frozen files. This script's own sha256
is pinned in the execution eligibility record.

Input pins (verified before deriving):
  manifest    5c318e3b48398ceec0dca1770dafcc82dc32dcebe729fd6eaa31d58ff748d259
  corpus      923dfd3d1ea48a80aacacd38ec24bb1da8c26879cddb95104a0338ff9e6606e2
  annotations cd04b32dec5464f10c71270f49b346d2d7b495e35a0e7c46e3c5d057e62400ae
  exclusions  f879efeaa6f89460e19bed686e5c24fef06d4c69f7d23e8902c1eecc05181888
  overlap     ed2522b8276dd0f1c9f7dea5fab1609e0d0f50883a7c8b7a5ac07044d181b8bc

Also runs the A' rollup verification against the committed artifacts
(63 scored / 7 unresolved; ambiguity 8 scored of 10) and REFUSES to
emit on any mismatch.
"""
import hashlib, json, sys
from pathlib import Path

D = Path(sys.argv[1] if len(sys.argv) > 1 else "tests/selfeval/thai-core-ai-v1")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else D / "thai-core-ai-v1.derived-view.json")

PINS = {
    "thai-core-ai-v1.manifest.json": "5c318e3b48398ceec0dca1770dafcc82dc32dcebe729fd6eaa31d58ff748d259",
    "thai-core-ai-v1.corpus.json": "923dfd3d1ea48a80aacacd38ec24bb1da8c26879cddb95104a0338ff9e6606e2",
    "thai-core-ai-v1.annotations.json": "cd04b32dec5464f10c71270f49b346d2d7b495e35a0e7c46e3c5d057e62400ae",
    "thai-core-ai-v1.exclusions.json": "f879efeaa6f89460e19bed686e5c24fef06d4c69f7d23e8902c1eecc05181888",
    "thai-core-ai-v1.overlap-report.json": "ed2522b8276dd0f1c9f7dea5fab1609e0d0f50883a7c8b7a5ac07044d181b8bc",
}
for name, want in PINS.items():
    got = hashlib.sha256((D / name).read_bytes()).hexdigest()
    if got != want:
        sys.exit(f"REFUSED: {name} hash {got} != pinned {want} (frozen inputs only)")

man = json.loads((D / "thai-core-ai-v1.manifest.json").read_text())
corpus = json.loads((D / "thai-core-ai-v1.corpus.json").read_text())
ann = json.loads((D / "thai-core-ai-v1.annotations.json").read_text())
ovl = json.loads((D / "thai-core-ai-v1.overlap-report.json").read_text())

recs = ann["annotation_records"]
by_pair = {}
for r in recs:
    by_pair.setdefault((r["item_id"], r["turn"]), []).append(r)
by_item = {}
for r in recs:
    by_item.setdefault(r["item_id"], []).append(r["annotation_id"])

fam = {a["annotator_id"]: a["family"] for a in man["provenance"]["annotators"]}
authfam = {a["author_id"]: a["family"] for a in man["provenance"]["authors"]}
corp_by_id = {it["id"]: it for it in corpus["items"]}

# --- A' rollup verification (independent recomputation) ---
EXPECTED = {"recall": 10, "unknown": 10, "contradiction": 10, "ambiguity": 10,
            "teach": 10, "forget": 10, "correction": 10}
items_view, cats = [], {}
n_scored = n_unres = 0
for it in man["items"]:
    iid = it["id"]
    c = corp_by_id[iid]
    if c.get("scored_turns"):
        expected_pairs = [(iid, st["turn"]) for st in c["scored_turns"]]
    else:
        # unresolved item: scored_turns is null in the corpus; expected pairs
        # are the (id, turn) pairs the annotation records actually cover
        expected_pairs = sorted(p for p in by_pair if p[0] == iid)
    ok, complete = True, True
    for p in expected_pairs:
        rs = by_pair.get(p, [])
        if len(rs) != 2 or len({fam[r["annotator_id"]] for r in rs}) != 2:
            complete = False
            ok = False
            continue
        if authfam[it["authored_by"]] in {fam[r["annotator_id"]] for r in rs}:
            sys.exit(f"REFUSED: author family annotated its own item {iid} (family exclusion)")
        if json.dumps(rs[0]["label"], sort_keys=True) != json.dumps(rs[1]["label"], sort_keys=True):
            ok = False
    # declared flags only (A' clarification): v1 has no flag mechanism -> none
    flagged = bool(it.get("critical") or it.get("ambiguous"))
    if flagged:
        state, reason = "unresolved", "no-independent-adjudicator"
    elif not complete:
        state, reason = None, None  # pending/partial: refuse below (frozen set must be complete)
    elif ok:
        state, reason = "scored", None
    else:
        state, reason = "unresolved", "annotator-disagreement"
    if state is None:
        sys.exit(f"REFUSED: {iid} has incomplete pairs in a CONTENT_FROZEN set")
    if it["disposition"] != state:
        sys.exit(f"REFUSED: {iid} frozen disposition {it['disposition']} != rollup {state}")
    if state == "unresolved" and it.get("unresolved_reason") != reason:
        sys.exit(f"REFUSED: {iid} frozen reason {it.get('unresolved_reason')} != rollup {reason}")
    view = {"id": iid, "category": it["category"], "origin": "authored",
            "authored_by": it["authored_by"], "ai_authored": True, "not_human_validated": True,
            "scored_turns": [t for (_, t) in expected_pairs],
            "annotation_progress": "complete",
            "annotation_ids": sorted(by_item.get(iid, [])),
            "disposition": state}
    if reason:
        view["unresolved_reason"] = reason
    items_view.append(view)
    cats.setdefault(it["category"], {"items": 0, "scored": 0, "unresolved": 0})
    cats[it["category"]]["items"] += 1
    cats[it["category"]][state if state == "scored" else "unresolved"] += 1
    n_scored += state == "scored"
    n_unres += state == "unresolved"

if not (n_scored == 63 and n_unres == 7 and cats["ambiguity"]["scored"] == 8):
    sys.exit(f"REFUSED: rollup {n_scored}/{n_unres} ambiguity {cats['ambiguity']['scored']} != expected 63/7/8")
print("rollup verified: 63 scored, 7 unresolved, ambiguity 8/10, dispositions match frozen manifest")

# --- derived view assembly ---
CRITERIA_SHA = "241612cab5f3efbec8eee2562e2850680a8a262186132cbe4af8ee6af7a2dd18"
GOLD = {"recall": "{supported, answer}", "unknown": "{unknown, abstain}",
        "contradiction": "{contradicted, answer}", "ambiguity": "{ambiguous, clarify}",
        "teach": "{supported, acknowledge}", "forget": "{unknown, acknowledge}",
        "correction": "{supported, acknowledge}"}
criteria = {c: (f"criteria v1 FROZEN (sha256 {CRITERIA_SHA}), category '{c}'; gold shape {g} "
                f"per the pinned closed schema (criteria doc Part 1 + Part 2b); the frozen criteria text is authoritative")
            for c, g in GOLD.items()}

sess = man["provenance"]["annotation_sessions"]
log = [{"annotation_id": r["annotation_id"], "item_id": r["item_id"], "turn": r["turn"],
        "session_id": r["session_id"], "annotator_id": r["annotator_id"], "batch_id": r["batch_id"],
        "criteria_version": r["criteria_version"], "label": r["label"],
        "response_hash": r["response_hash"], "timestamp": r["date"],
        "prompt_template_hash": r["prompt_template_hash"]} for r in recs]

preflight = [{"category": c, "usable_examples": 5, "structural_pass": 5, "instruction_pass": 5,
              "task_matches": 5, "outcome": "pass", "reviewers": ["claude", "gpt"],
              "evidence_ref": "evidence/preflight-review/{gpt,claude}-score-sheet.md (protocol preflight-v2, both reviewers PASS 5/5/5/5 on all 7 categories)"}
             for c in ["recall", "unknown", "contradiction", "ambiguity", "teach", "forget", "correction"]]

pins = ovl["pins"]
overlap = {"dev_set_hash": pins["dev_set_sha256"],
           "overlap_checker_hash": pins["checker_sha256"],
           "tokenizer_hash": "1835b0c9dcba721172a7910cd4100256fe36a0c8eae78a47952072c078444d09",
           "dictionary_hash": "35f65d43ea83b5b981134d5edc3b9afcb64b4ba96146900fc4d312f2940c3265",
           "normalization_config": pins["normalization"],
           "sequence_algorithm": pins["sequence_algorithm"],
           "min_meaningful_length": pins["thresholds"]["min_meaningful_chars"],
           "thresholds": pins["thresholds"],
           "note": "operational thresholds, not proven semantic-duplicate detection",
           "report_ref": "thai-core-ai-v1.overlap-report.json (sha256 pinned in attestation); outcome: " + ovl["outcome"]}

att = {"manifest_hash": PINS["thai-core-ai-v1.manifest.json"],
       "corpus_hash": PINS["thai-core-ai-v1.corpus.json"],
       "ledger_head_hash": "9cfde10225d97257b3ea9426874412c64d6cd92ce91be36e3db9c442ccc15416",
       "variation_plan_hash": "01d6b719483d2e6f47f0751b3311423ba6cd275948ba6f9bc199283090a130b3",
       "criteria_hash": CRITERIA_SHA,
       "session_log_hash": PINS["thai-core-ai-v1.annotations.json"],
       "annotation_log_hash": PINS["thai-core-ai-v1.annotations.json"],
       "raw_responses_hash": "655d960e43f50a322d3e9ce4ef44550342b510ebe38405039d39158c1bbad757",
       "overlap_report_hash": PINS["thai-core-ai-v1.overlap-report.json"],
       "prompt_templates_hash": "0ff7e325ac7a98f20a16dce37afc1560e98f5ae1b5127148b8372d24093eccf4",
       "harness_build_hash": "906026955f6d81bce449486cf3cd23e2af0362579a776cbbb739c58b91571ae9",
       "anchor": {"repo": "github.com/Ashveil1/holyshit", "commit": "d800d4396939d756c04b27c6e7d2f50d6cbc9edc"},
       "note": ("Pins name the FROZEN artifacts (commit d800d43, full table in "
                "docs/thai/thai-core-ai-v1-freeze-attestation.md). session_log_hash/annotation_log_hash both "
                "pin thai-core-ai-v1.annotations.json, the single session+decision log of record; "
                "raw_responses_hash pins corpus-gemini/SHA256SUMS whose per-file hashes cover every raw "
                "response (cross-gpt/cross-claude SHA256SUMS pinned in the same attestation).")}

view = {"id": "thai-core-ai-v1", "version": 1, "kind": "thai-dataset", "lang": "th",
        "tier": "supported", "status": "AI_AUTHORED_CONTENT_FROZEN", "annotation_variant": "A",
        "label": "AI-authored / not human-validated",
        "derived": {"non_normative": True,
                    "note": ("DERIVED VIEW, non-normative. Canonical artifacts: the five frozen files under "
                             "tests/selfeval/thai-core-ai-v1/ at commit d800d43. Generated deterministically by "
                             "scripts/thai-derived-view.py (hash pinned in the eligibility record) per the "
                             "2026-11-27 spec 4.4 A' clarification: per-(id, turn) records, item rollup = "
                             "agreement on every scored turn; critical/ambiguous = declared item flags only "
                             "(v1: zero declared flags under the v1 process, recorded limitation)."),
                    "source_commit": "d800d4396939d756c04b27c6e7d2f50d6cbc9edc",
                    "generated_by": "scripts/thai-derived-view.py",
                    "input_hashes": PINS},
        "provenance": {"method": "ai-authored", "human_validated": False,
                       "authors": man["provenance"]["authors"], "annotators": man["provenance"]["annotators"],
                       "annotation_sessions": sess, "criteria_version": "v1",
                       "variation_plan_hash": att["variation_plan_hash"]},
        "corpus": {"file": "thai-core-ai-v1.corpus.json", "sha256": PINS["thai-core-ai-v1.corpus.json"]},
        "acceptance_criteria": criteria,
        "items": items_view,
        "evidence": {"annotation_log": log, "preflight_log": preflight, "overlap_report": overlap,
                     "exclusion_ledger": [], "freeze_attestation": att}}

OUT.write_text(json.dumps(view, ensure_ascii=False, indent=1))
h = hashlib.sha256(OUT.read_bytes()).hexdigest()
print(f"derived view -> {OUT} sha256 {h}")
print("per-category:", {c: f"{v['scored']}/{v['items']}" + (f" (+{v['unresolved']} unresolved)" if v['unresolved'] else "") for c, v in sorted(cats.items())})
