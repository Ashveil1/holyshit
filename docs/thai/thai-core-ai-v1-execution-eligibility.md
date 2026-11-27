# thai-core-ai-v1 - EXECUTION ELIGIBILITY record (spec v2.5 section 7.3)

Date: 2026-11-27. Label: AI-authored / not human-validated.
STATUS: ACTIVE. Decision: ELIGIBLE, recorded 2026-11-27 by the hs-ai
task agent under Ash's 22 Nov delegation + 26 Nov "continue all",
routed via main, after PR #463 (thai-check A' alignment) merged to
master (44d2f808) and the merged-tree thai-check re-verified clean
(verbatim below). This record pins the corpus hash and gates the first
harness run; the frozen set is never run without it.

## Frozen set (commit d800d4396939d756c04b27c6e7d2f50d6cbc9edc)

- Manifest  thai-core-ai-v1.manifest.json
  sha256 5c318e3b48398ceec0dca1770dafcc82dc32dcebe729fd6eaa31d58ff748d259
  status AI_AUTHORED_CONTENT_FROZEN, 70 items (63 scored, 7 unresolved)
- Scenario corpus  thai-core-ai-v1.corpus.json
  sha256 923dfd3d1ea48a80aacacd38ec24bb1da8c26879cddb95104a0338ff9e6606e2
- Freeze attestation  docs/thai/thai-core-ai-v1-freeze-attestation.md
  (full pin table; anchor d800d43)
- Spec 4.4 A' clarification  docs/thai/thai-spec-v2.5-section-4.4-clarification-A-prime.md
  (ratified 2026-11-27; critical/ambiguous = declared item flags only;
  both consult families chose A')

## Checker identity

- In-agent checker: agent/selfeval.holy thai-check AI path, merged to
  master as PR #463, merge commit 44d2f808 (item-level flags +
  per-(id,turn) A' rollup; label trigger dropped).
- Derived view: tests/selfeval/thai-core-ai-v1/thai-core-ai-v1.derived-view.json
  sha256 18d948221395ee5e6124fcf38e47370532ad6f8009f7fa2f49d68e20bf113f9d
  (non-normative; merged byte-identical in #463)
- Derivation script: scripts/thai-derived-view.py
  sha256 2439dc8118edeff9cf3df0063a5bf14dc2aca173b0066f1b59fe4ad5733e7113

## Recorded thai-check output (MERGED tree, exec branch b9a085d = master 44d2f808 + frozen suite; interp route, 2026-11-27 13:20 UTC, verbatim)

    thai-check thai-core-ai-v1 v1 tier supported status AI_AUTHORED_CONTENT_FROZEN variant A (AI-authored / not human-validated: format and evidence check only - no labels created, no scoring here, NEVER a quality claim; tier declares capability scope only; SHA-256 fields are shape- and chain-checked, recomputation is external until C20)
      ambiguity: 8 scored of 10 items, 2 unresolved
      contradiction: 10 scored of 10 items
      correction: 8 scored of 10 items, 2 unresolved
      forget: 9 scored of 10 items, 1 unresolved
      recall: 10 scored of 10 items
      teach: 10 scored of 10 items
      unknown: 8 scored of 10 items, 2 unresolved
    verdict: CONTENT_FROZEN: evidence complete (execution eligibility is a separate external record; the frozen set is never run before it)

63 scored / 7 unresolved / 0 problems. Identical to the pre-merge
recording against #463 head 970c20e.

## C19 route parity (SEPARATE serialization corpus, never the frozen set)

- C19: PR #452, commit cf1229ed7d18ee1fc7765c8f93fa257b45f0e83b, on master.
- Parity evidence (real run 2026-11-27 03:57 UTC, tests/test_json_str_routes.py, verbatim tail):
      ok json_str ir-x64 224 lines byte-identical
      ok json_str ast-x64 224 lines byte-identical
      ok json_str seed-native 224 lines byte-identical
      ok json_str hs-interpreter 224 lines byte-identical
      5/5 json_str routes byte-identical + CPython-oracle-identical
  (5 routes as the test enumerates them.)

## Harness identity

- scripts/thai-core-harness.py
  sha256 5ef5c06573ccb721d3c406c4ec8d04ba3c65d88299487af3ae391f024f07f89a
  CHANGE DISCLOSED (2026-11-27, pre-first-execution): the hash-pinned
  source changed from 906026955f... (freeze attestation value) to
  5ef5c06573... before any execution. Two execution-mechanics fixes,
  no scoring or selection semantics touched: (1) every scenario now
  runs in a FRESH TEMP DIRECTORY, because repl.holy persists
  agent-memory.json to its cwd and sequential runs would otherwise
  leak taught state between scenarios (contamination bug caught
  pre-flight, verified: the repl writes agent-memory.json to cwd);
  (2) added --binary (run a prebuilt native repl), --skip/--limit
  (chunked execution with id-based slice merging). Refusal behavior
  unchanged: verified 2026-11-27 to refuse without this record.
- Examinee build for the first run: native repl binary built from
  b9a085d (exec branch; `git diff 44d2f808..HEAD` over agent/ native/
  runtime/ compiler/ seed/ x64gen/ hs.py is EMPTY - identical code to
  merged master 44d2f808), `python3 hs.py build agent/repl.holy`,
  binary sha256 82167169d241a0a6a15fcc04ed983879d72617e71ef98f1d015e7c480b98be30,
  run with LD_LIBRARY_PATH for the gc runtime. Route parity evidence:
  corpus byte-identity suite + C19 5/5 above; the interp route remains
  available for cross-checks.

## Run record

Run 1 (2026-11-27 13:23 UTC): EXECUTED. Harness 5ef5c06573...,
native repl binary 82167169d241... (code identical to master 44d2f808),
63/63 scored items captured, each in a fresh temp cwd (no cross-scenario
state). Verbatim harness output:
    captured 63 items this slice (63/63 total) -> tests/selfeval/thai-core-ai-v1.replies-v001.json
Replies file: tests/selfeval/thai-core-ai-v1.replies-v001.json
    sha256 e5a0148366d6ed608b9178f771319a6a24d97c5a9704bad3c98d24e38e71523b
MEASURED RESULT (raw, unscored): every corpus turn in every scenario
received the reply "i do not understand" - the v0.17 repl grammar
accepts none of the frozen corpus's natural Thai scenario phrasings.
This is the instrument's baseline measurement, not a quality claim and
not a bug in the frozen set. Formal scoring against the gold labels
requires the external scorer (versioned, hash-pinned before use); the
raw replies already show the outcome unambiguously. AI-authored /
not human-validated.
