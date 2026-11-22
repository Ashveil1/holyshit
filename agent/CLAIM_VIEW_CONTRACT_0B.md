# Claim view contract claimview-0b (DRAFT for freeze consult)

Supersedes claimview-0a for any implementation. `claimview-0a`, `fixtures-0a.json` and caps v1 stay immutable and are NOT edited. 0b states only what differs or is added; everything in 0a not mentioned here (sections 1, 2 wording, 5, 6 privacy pipeline, 7 ordering/caps, 8, 9) carries over unchanged. Status: SPEC ONLY. No Holy code, REPL route, release or parity claim. Parity with the 39 characterization scenarios is NOT correctness or completeness evidence. Source of verdict: A24.0b fork verdict F1-F8.

## 1. Result layers (new)
Every view returns one outer layer:
- COMPLETE: the in-scope search was exhausted for both polarities as required by section 5. Only here may a status appear: SUPPORTED, CONTRADICTED, UNKNOWN, or AMBIGUOUS (subject alias ambiguity, 0a section 3/4 rows).
- OUT_OF_SCOPE: shape, predicate, negation or identity not covered by 0b. Reason codes: `predicate_unsupported`, `negation_unsupported`, `shape_unsupported` (free-form value with no relation, subject-only, reference word), `identity_collision`. No evidence, counts, candidates or status are shown. Never rendered as UNKNOWN.
- INCOMPLETE: a depth or work bound stopped the search before completeness could be established. Reason codes: `depth_limit`, `work_limit`. No status and no partial evidence is shown as a verdict. Never rendered as UNKNOWN or "no trusted support".
Readings (0a section 6 rules unchanged) are shown only in the COMPLETE layer. OUT_OF_SCOPE and INCOMPLETE show no readings.

## 2. Scope profile (F7)
Identity is exact canonical (0a section 3 canonicalization), with no article stripping. "a robin" and "robin" are different identities.
In scope (stored tuple predicate names are the engine's):
- `is-a`: positive and negative (`not-is-a`) via is-a inheritance chain.
- `has`: positive and negative (`not-has`), including inheritance down is-a.
- `is-in`: direct edge, plus positive transitive chaining over is-in edges only. No negation, no is-a inheritance. A stored or asked negative is-in is OUT_OF_SCOPE `negation_unsupported`.
- `means`: direct stored edge only (no chaining), positive only.
OUT_OF_SCOPE `predicate_unsupported`: can, uses, produces, needs, causes, and anything else. Negation is valid only for is-a and has. Phrase mapping ("is" to is-a, "in" to is-in) belongs to the A24.1 parser adapter, not the view. The view takes already-structured (subject, predicate, object, polarity).
No rule-derived (`_RULES`) proofs exist in 0b. Consequently no guard exists to block: the guard-blocked note (F4) is RESERVED and is not emitted in 0b. Its future conditions: only for the current query and path, only when a guard actually blocked a candidate path AND a complete strict search found no proof for that exact proposition and polarity, naming the grounded intermediate subject, never evidence or status, never from stale `gfail`.
Hypotheses, explore-mode assumptions, `_derive_render` and cooc hints are never read.

## 3. Identity safety (F2) and aliases (F3)
- Subject resolution is the 0a rule: exact canonical key, or exact taught alias whose target key exists (NONE / UNIQUE / AMBIGUOUS, dangling aliases ignored, no fuzzy or reading-based resolution). Resolution happens in the view before any search.
- Edge subjects and objects are read as stored tuples (original strings), not through any article-stripped bucket key.
- Collision scan: before a search is trusted, every node the search reaches (subject, intermediates, objects, and the asked object) is checked. If two distinct canonical strings in the reached set have the same article-stripped form (leading "a " or "an "), the result is OUT_OF_SCOPE `identity_collision` with no evidence. Differential tests against the engine run only on collision-free states.

## 4. Search semantics (F1): nearest level, both polarities
Level 0 is edges stored on the subject itself. Level k (k>=1) is edges on nodes first reached by following is-a edges k times from the subject (shortest-path level; each node has one level, visited set).
For the asked (predicate, object):
- is-a: the object is reached at level k if an is-a edge into it exists from a node at level k-1 (a stored direct edge is level 1 from the subject; positive support). A stored `not-is-a` edge from a node at level k-1 to the object is opposition at level k.
- has: a `has` / `not-has` edge from a node at level k to the object is evidence at level k.
- is-in: positive chain support only (BFS over is-in edges, shortest levels).
- means: direct only, level 0.
Selection: find the smallest level k holding any evidence of either polarity. Show ALL evidence at that level, both polarities (support and opposition, capped as 0a). Deeper evidence is ignored and not reported. Both polarities present at level k gives CONTRADICTED both_sides. The view says explicitly: "nearest-level result, not an inventory of every reachable edge". A first result never hides a same-level contradiction.
Provenance: level-0 stored edge = stored; inherited or chained = derived (dependent on every edge on its path, not corroboration). Built-in means: provenance `builtin` (section 7).
Truth table is 0a section 4 with those evidence sets. UNKNOWN only inside COMPLETE.

## 5. Completeness (F5), bounded computation
The view runs its own search (not `_rule_prove`, `pseen` or `memo`; not the engine's first-result path). Bounds: is-a depth bound D=8 levels; work bound W=500 edge examinations per view (version 1 values, recorded in the output as `bounds`). The bound limits computation, not only output.
- Search level by level up to the nearest evidence level k. COMPLETE iff levels 0..k are fully expanded for both polarities within D and W.
- With no evidence found: COMPLETE UNKNOWN only if the search exhausted the reachable is-a closure (frontier empty) within D and W. If an unexpanded frontier remains at depth D: INCOMPLETE `depth_limit`. If W is exceeded: INCOMPLETE `work_limit`.
- With evidence at level k <= D whose levels were exhausted: COMPLETE even if a farther frontier remains (nearer wins by section 4).
- One polarity complete while the other hits a limit before the nearest level is settled: INCOMPLETE (both polarities are required).
- Cycles: the visited set cuts them; a cycle never makes a result INCOMPLETE by itself.
- Display caps (5/5/5, root 0, display depth 2, 20 nodes) are rendering caps only and never decide completeness. Truncation is counted after eligibility and reported as in 0a.

## 6. Purity (F6)
The view reads core state and writes nothing: no `_derive_render`, no hypothesis record, no counters or caches. Any engine call used by tests or differentials runs on an isolated deep copy of state with mode forced to strict, and must leave the original and all state keys byte-identical (repeatability test).

## 7. Built-in provenance (F8)
Declarative built-in `means` definitions (`_BUILTIN_RELS`) appear with provenance `builtin`: "built-in definition; not user-taught; not independent evidence". Ordinary forget never removes them. A built-in plus a taught edge for the same claim are two displayed lines but NOT two independent sources and never counted as corroboration.

## 8. Versioning and fixtures
New files only: `agent/CLAIM_VIEW_CONTRACT_0B.md`, `tests/claimview/fixtures-0b.json`. caps v1 unchanged. The 39 real-core scenarios (`scenarios-0b.json`) are reviewed fixtures for the Oracle differential on collision-free in-scope cases only; expected outcomes in `fixtures-0b.json` are derived from this contract, not copied from engine output.
Required test families before any implementation claim: per-predicate and polarity in/out of scope; nearest-level plus same-level both polarities; search order changes, shared intermediates, cycles, depth boundary (8 vs 9 vs 10 links), work-limit; one-polarity-complete-other-limited; identity collision; alias NONE/UNIQUE/AMBIGUOUS/dangling; strict-copy isolation and no mutation over all state; builtin provenance and forget; privacy exclusion and malformed exclusion (0a); interp/native differentials including non-ASCII; ordinary replies and 7-route corpus byte-identical; no new user-facing route.
