#!/usr/bin/env python3
"""thai-overlap-check: spec v2.5 section 5 overlap gate, thai-core-ai-v1
scenario corpus vs the thai-dev-ai-v1 dev set. Screening, not
independence. All inputs pinned in the emitted report.

Units: whole scenario AND every individual line (both sets).
Methods (deterministic):
  - exact normalized match (NFC, whitespace fold, case fold): REJECT
  - token-set Jaccard >= 0.80: FLAG; >= 0.95: REJECT only when the text
    is at least MIN_LEN normalized chars (else FLAG)
  - sequence-aware ratio (difflib.SequenceMatcher, autojunk=False)
    alongside Jaccard: >= 0.85 FLAG (never auto-reject)
  - containment for texts under 5 tokens: FLAG, never auto-reject
"""
import hashlib, json, sys, unicodedata, difflib
from pathlib import Path

JAC_FLAG, JAC_REJECT, SEQ_FLAG, MIN_LEN, MIN_TOKENS = 0.80, 0.95, 0.85, 20, 5

def norm(s):
    return " ".join(unicodedata.normalize("NFC", s).split()).casefold()

def tokens(s):
    from pythainlp.tokenize import word_tokenize
    return [t for t in word_tokenize(norm(s), engine="newmm") if t.strip()]

def jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa or not sb: return 0.0
    return len(sa & sb) / len(sa | sb)

def main(corpus_path, dev_path, out_md):
    import pythainlp, pythainlp.corpus.common as common
    dict_path = None
    for name in ("_THAI_WORDS_FILENAME", "THAI_WORDS"):
        dict_path = getattr(common, name, None) or dict_path
    cor = json.loads(Path(corpus_path).read_text())
    dev = json.loads(Path(dev_path).read_text())
    cor_hash = hashlib.sha256(Path(corpus_path).read_bytes()).hexdigest()
    dev_hash = hashlib.sha256(Path(dev_path).read_bytes()).hexdigest()

    # units: (set_id, unit_id, text)
    units_c = []
    for it in cor["items"]:
        units_c.append((it["id"], "whole", "\n".join(it["turns"])))
        for n, t in enumerate(it["turns"], 1):
            units_c.append((it["id"], f"line-{n}", t))
    units_d = []
    scen = {}
    for it in dev["items"]:
        units_d.append((it["id"], "input", it["input"]))
        scen.setdefault(it.get("scenario", ""), []).append(it["input"])
    for sid, lines in scen.items():
        units_d.append((sid, "whole", "\n".join(lines)))

    # namespaces (5.3): corpus ids vs dev ids must be disjoint
    ns_ok = not ({u[0] for u in units_c} & {u[0] for u in units_d})

    flagged, rejected = [], []
    ncmp = 0
    for cid, cunit, ctext in units_c:
        cn, ct = norm(ctext), tokens(ctext)
        for did, dunit, dtext in units_d:
            dn, dt = norm(dtext), tokens(dtext)
            ncmp += 1
            pair = {"corpus": f"{cid}:{cunit}", "dev": f"{did}:{dunit}"}
            if cn == dn:
                rejected.append({**pair, "method": "exact-normalized"})
                continue
            j = jaccard(ct, dt)
            sr = difflib.SequenceMatcher(None, cn, dn, autojunk=False).ratio()
            small = min(len(ct), len(dt)) < MIN_TOKENS
            contained = small and (set(ct) <= set(dt) or set(dt) <= set(ct)) and (ct and dt)
            if j >= JAC_REJECT and min(len(cn), len(dn)) >= MIN_LEN and not small:
                rejected.append({**pair, "method": "jaccard", "jaccard": round(j, 4), "seq": round(sr, 4)})
            elif j >= JAC_FLAG or sr >= SEQ_FLAG or contained:
                why = []
                if j >= JAC_FLAG: why.append(f"jaccard {j:.3f}")
                if sr >= SEQ_FLAG: why.append(f"seq {sr:.3f}")
                if contained: why.append("containment (<5 tokens)")
                flagged.append({**pair, "why": ", ".join(why), "jaccard": round(j, 4), "seq": round(sr, 4),
                                "corpus_text": ctext[:120], "dev_text": dtext[:120]})

    pins = {
        "corpus_sha256": cor_hash, "dev_set_sha256": dev_hash,
        "checker": "scripts/thai-overlap-check.py",
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "tokenizer": f"pythainlp {pythainlp.__version__} word_tokenize engine=newmm",
        "tokenizer_dict": dict_path or "package default",
        "normalization": "Unicode NFC, whitespace folding, case folding (casefold)",
        "sequence_algorithm": "Python 3.10.12 difflib.SequenceMatcher ratio, autojunk=False",
        "thresholds": {"jaccard_flag": JAC_FLAG, "jaccard_reject": JAC_REJECT,
                       "seq_flag": SEQ_FLAG, "min_meaningful_chars": MIN_LEN,
                       "min_tokens_containment": MIN_TOKENS},
        "units": "whole scenario AND every individual line, both sets",
        "comparisons": ncmp, "namespace_disjoint": ns_ok,
    }
    rpt = {"report": "thai-core-ai-v1 overlap gate (screening, not independence; thresholds OPERATIONAL, not proven semantic-duplicate detection)",
           "label": "AI เขียน / not human-validated", "date": "2026-11-27",
           "pins": pins, "rejected": rejected, "flagged": flagged}
    Path(out_md).write_text(json.dumps(rpt, ensure_ascii=False, indent=1))
    print(f"comparisons {ncmp} | rejected {len(rejected)} | flagged {len(flagged)} | namespaces disjoint: {ns_ok}")
    for r in rejected[:5]: print("  REJECT:", r)
    for f in flagged[:10]: print("  FLAG:", f["corpus"], "vs", f["dev"], "-", f["why"])

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
