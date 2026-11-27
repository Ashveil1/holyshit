#!/usr/bin/env python3
"""thai-ai-check: structural checker for the AI-authored thai-core suite
(spec v2.5 sections 3.1-3.5, 4.4-4.6, 6). Operates on the manifest; the
scenario corpus and evidence are referenced by hash. Exit 0 = clean.

Usage: python3 scripts/thai-ai-check.py tests/selfeval/thai-core-ai-v1/
"""
import hashlib, json, sys
from pathlib import Path

FAMS = {"claude", "gpt", "gemini"}
UNRES = {"annotator-disagreement", "no-independent-adjudicator"}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(o): return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

def main(d):
    d = Path(d)
    errs, notes = [], []
    man = json.loads((d / "thai-core-ai-v1.manifest.json").read_text())
    cor = json.loads((d / "thai-core-ai-v1.corpus.json").read_text())
    led = json.loads((d / "thai-core-ai-v1.exclusions.json").read_text())
    log = json.loads((d / "thai-core-ai-v1.annotations.json").read_text())

    # --- provenance (3.1) ---
    p = man.get("provenance", {})
    if p.get("method") != "ai-authored": errs.append("provenance.method != ai-authored")
    if p.get("human_validated") is not False: errs.append("human_validated must be the literal false")
    authors = p.get("authors", [])
    for a in authors:
        if a.get("family") not in FAMS: errs.append(f"author {a.get('author_id')}: bad family")
        for k in ("author_id", "model", "version", "session_date"):
            if k not in a: errs.append(f"author {a.get('author_id')}: missing {k}")
    annotators = p.get("annotators", [])
    ids = [a.get("annotator_id") for a in annotators]
    if len(ids) != len(set(ids)): errs.append("duplicate annotator identity")
    for a in annotators:
        if a.get("family") not in FAMS: errs.append(f"annotator {a.get('annotator_id')}: bad family")
        if "version" not in a: errs.append(f"annotator {a.get('annotator_id')}: missing version")
    sess = p.get("annotation_sessions", [])
    sids = [s.get("session_id") for s in sess]
    if len(sids) != len(set(sids)): errs.append("sessions share an id")
    ann_by_id = {a["annotator_id"]: a for a in annotators}
    for s in sess:
        if s.get("annotator_id") not in ann_by_id: errs.append(f"session {s.get('session_id')}: unknown annotator")
        for k in ("session_date", "batch_id", "displayed_model_label", "prompt_template_hash", "item_order_seed"):
            if k not in s: errs.append(f"session {s.get('session_id')}: missing {k}")
        if "resume_of" not in s: errs.append(f"session {s.get('session_id')}: missing resume_of (null allowed)")
    if not p.get("criteria_version") or not p.get("variation_plan_hash"):
        errs.append("missing criteria_version or variation_plan_hash")

    # --- annotation log (4.6) ---
    recs = {r["annotation_id"]: r for r in log["annotation_records"]}
    if len(recs) != len(log["annotation_records"]): errs.append("duplicate annotation_id in log")
    sess_by_id = {s["session_id"]: s for s in sess}
    for r in recs.values():
        if r["annotator_id"] not in ann_by_id: errs.append(f"{r['annotation_id']}: unknown annotator")
        if r["session_id"] not in sess_by_id: errs.append(f"{r['annotation_id']}: unknown session")
        if not r.get("response_hash"): errs.append(f"{r['annotation_id']}: missing response_hash")
        lab = r.get("label", {})
        if lab.get("epistemic") not in {"supported", "unknown", "contradicted", "ambiguous", "n/a"}:
            errs.append(f"{r['annotation_id']}: bad epistemic")
        if lab.get("action") not in {"answer", "abstain", "clarify", "acknowledge", "not_understood", "other"}:
            errs.append(f"{r['annotation_id']}: bad action")

    # --- items (3.3, 3.4) ---
    auth_by_id = {a["author_id"]: a for a in authors}
    seen_ids = set()
    per_cat = {}
    n_scored = n_unres = 0
    for it in man["items"]:
        iid = it["id"]
        if iid in seen_ids: errs.append(f"duplicate item {iid}")
        seen_ids.add(iid)
        per_cat[it["category"]] = per_cat.get(it["category"], 0) + 1
        if it.get("ai_authored") is not True: errs.append(f"{iid}: ai_authored must be true")
        if it.get("not_human_validated") is not True: errs.append(f"{iid}: not_human_validated must be true")
        au = auth_by_id.get(it.get("authored_by"))
        if not au: errs.append(f"{iid}: unknown author"); continue
        # family-level invariant (3.4)
        arecs = [recs.get(a) for a in it.get("annotation_ids", [])]
        if any(r is None for r in arecs):
            errs.append(f"{iid}: annotation_ids reference missing records"); continue
        afams = {ann_by_id[r["annotator_id"]]["family"] for r in arecs}
        if au["family"] in afams:
            errs.append(f"{iid}: author family {au['family']} appears among annotator families")
        # progress x disposition (3.3)
        prog, disp = it.get("annotation_progress"), it.get("disposition")
        if prog not in {"pending", "partial", "complete"}: errs.append(f"{iid}: bad progress {prog}")
        if disp == "scored" and prog != "complete":
            errs.append(f"{iid}: scored from non-complete state")
        if prog == "complete" and disp not in {"scored", "unresolved"}:
            errs.append(f"{iid}: complete without disposition")
        if disp == "unresolved":
            if it.get("unresolved_reason") not in UNRES:
                errs.append(f"{iid}: bad unresolved_reason {it.get('unresolved_reason')}")
            n_unres += 1
        elif disp == "scored":
            n_scored += 1
        # two family-distinct annotations per scored turn, one gemini (variant A)
        turns = {}
        for r in arecs:
            turns.setdefault(r["turn"], []).append(r)
        for t, rs in turns.items():
            fs = [ann_by_id[r["annotator_id"]]["family"] for r in rs]
            if len(rs) != 2 or len(set(fs)) != 2:
                errs.append(f"{iid} turn {t}: needs exactly two family-distinct annotations")
            if "gemini" not in fs:
                errs.append(f"{iid} turn {t}: variant A requires a gemini annotation")
    for c in man["categories"]:
        if per_cat.get(c) != 10: errs.append(f"category {c}: {per_cat.get(c)} items, expected 10")
    notes.append(f"items {len(man['items'])}, scored {n_scored}, unresolved {n_unres}")
    if man["counts"] != {"items": len(man["items"]), "per_category": 10, "scored": n_scored, "unresolved": n_unres}:
        errs.append("manifest counts block disagrees with items")

    # --- corpus consistency ---
    cids = [i["id"] for i in cor["items"]]
    if sorted(cids) != sorted(seen_ids): errs.append("corpus/manifest item-id mismatch")
    if cor.get("label") != "AI เขียน / not human-validated": errs.append("corpus missing honesty label")
    mdis = {i["id"]: i for i in man["items"]}
    for ci in cor["items"]:
        if mdis[ci["id"]]["disposition"] == "scored":
            if not ci.get("scored_turns"): errs.append(f"{ci['id']}: scored item without corpus labels")
        else:
            if ci.get("scored_turns") is not None: errs.append(f"{ci['id']}: unresolved item carries gold labels")

    # --- exclusion ledger (6) ---
    entries = led.get("entries", [])
    if not entries or entries[0].get("kind") != "genesis":
        errs.append("ledger missing genesis entry")
    else:
        g = entries[0]
        expect_prev = hashlib.sha256(canon({"genesis_of": "thai-core-ai-v1", "manifest_sha256": sha(d / "thai-core-ai-v1.manifest.json")})).hexdigest()
        if g.get("prev_entry_hash") != expect_prev: errs.append("ledger genesis does not chain to the manifest hash")
        e = dict(g); ehash = e.pop("entry_hash", None)
        if hashlib.sha256(canon(e)).hexdigest() != ehash: errs.append("ledger genesis entry_hash mismatch")
        prev = ehash
        for e in entries[1:]:
            if e.get("prev_entry_hash") != prev: errs.append(f"ledger seq {e.get('seq')}: broken chain")
            c = dict(e); h = c.pop("entry_hash", None)
            if hashlib.sha256(canon(c)).hexdigest() != h: errs.append(f"ledger seq {e.get('seq')}: hash mismatch")
            prev = h

    for n in notes: print("note:", n)
    if errs:
        print(f"AI-CHECK FAIL ({len(errs)} problems)")
        for e in errs: print(" -", e)
        return 1
    print(f"AI-CHECK CLEAN: {len(man['items'])} items, {n_scored} scored, {n_unres} unresolved, "
          f"{len(recs)} annotation records, {len(sess)} sessions, ledger head {entries[-1].get('entry_hash', '')[:16]}...")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "tests/selfeval/thai-core-ai-v1"))
