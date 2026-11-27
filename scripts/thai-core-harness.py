#!/usr/bin/env python3
"""thai-core-harness: evaluation harness for the frozen thai-core-ai-v1
scenario corpus (spec v2.5 section 3.5: a separate, versioned component
that CONSUMES the scenario corpus and invokes the agent's execution
routes, one repl subprocess per scenario).

EXECUTION IS GATED. This harness runs ONLY after the external EXECUTION
ELIGIBILITY record exists (spec section 7.3): frozen manifest + corpus
hashes, C19 implementation/build identity, seven-route parity evidence
(on the SEPARATE Thai serialization test corpus, never this set),
harness hash, decision and date. Until then it is source only, pinned
by content hash in the freeze attestation. Parity testing must never
execute the frozen set.

Usage (only when eligible):
  python3 scripts/thai-core-harness.py --corpus tests/selfeval/thai-core-ai-v1/thai-core-ai-v1.corpus.json \
      --examinee-build <build-hash-or-binary-id> --out tests/selfeval/thai-core-ai-v1.replies-v001.json

Per scored item it spawns `python3 hs.py run agent/repl.holy`, feeds
the item's turns one per line, then 'quit', captures stdout, and
records the agent's reply lines per scored turn. Output carries the
label "AI-authored / not human-validated" and the examinee build field
(the replies-vXXX.json pattern extended with a build field). Unresolved
items are never executed.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_scenario(turns, timeout=300):
    r = subprocess.run(
        [sys.executable, str(ROOT / "hs.py"), "run", str(ROOT / "agent" / "repl.holy")],
        input="\n".join(turns + ["quit"]) + "\n",
        capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"repl exited {r.returncode}: {r.stderr[-400:]}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--examinee-build", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--eligibility-record", required=True,
                    help="path to the external EXECUTION ELIGIBILITY record; must exist and pin this corpus hash")
    a = ap.parse_args()

    corpus_path = Path(a.corpus)
    corpus_hash = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    elig = Path(a.eligibility_record)
    if not elig.exists():
        sys.exit("REFUSED: no execution eligibility record (spec 7.3); this set is never run without one")
    if corpus_hash not in elig.read_text():
        sys.exit("REFUSED: eligibility record does not pin this corpus hash")

    corpus = json.loads(corpus_path.read_text())
    replies = {"suite": corpus["id"], "version": corpus["version"],
               "label": "AI-authored / not human-validated",
               "corpus_sha256": corpus_hash,
               "harness": "scripts/thai-core-harness.py",
               "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "examinee_build": a.examinee_build,
               "items": []}
    for it in corpus["items"]:
        if it.get("scored_turns") is None:
            continue  # unresolved pool: never executed
        out = run_scenario(it["turns"])
        replies["items"].append({"id": it["id"], "stdout": out,
                                 "scored_turns": it["scored_turns"]})
    Path(a.out).write_text(json.dumps(replies, ensure_ascii=False, indent=1))
    print(f"captured {len(replies['items'])} scored items -> {a.out}")


if __name__ == "__main__":
    main()
