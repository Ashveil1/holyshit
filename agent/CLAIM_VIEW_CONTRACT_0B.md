# Claim view contract claimview-0b (revision 2, DRAFT for re-freeze consult)

Supersedes claimview-0a for any implementation. `claimview-0a`, `fixtures-0a.json` and caps v1 stay immutable and are NOT edited. 0b states only what differs or is added; everything in 0a not mentioned here (sections 1, 2 wording, 5, 6 privacy pipeline, 7 ordering/caps, 8, 9) carries over unchanged. Status: SPEC ONLY. No Holy code, REPL route, release or parity claim. Parity with the 39 characterization scenarios is NOT correctness or completeness evidence. Source: A24.0b verdicts F1-F8 and freeze edits B1-B8.

## 1. Result layers
Every view returns one outer layer:
- COMPLETE: resolution finished and, where a search is needed, the in-scope search was exhausted as section 5 requires. Only here may a status appear: SUPPORTED, CONTRADICTED, UNKNOWN, AMBIGUOUS (subject).
- OUT_OF_SCOPE: shape, predicate, negation or identity not covered. Reasons: `predicate_unsupported`, `negation_unsupported`, `shape_unsupported` (free-form value, subject-only, reference word), `identity_collision`. No evidence, counts, candidates, status, or colliding strings are shown or named.
- INCOMPLETE: a bound stopped the search before completeness. Reasons: `depth_limit`, `work_limit`. No status and no partial support or opposition is shown. Never rendered as UNKNOWN.
Output may state the configured bounds (D, W). It never states actual work counts, examined edges, or hidden identities.
Readings (0a section 6 unchanged) appear only in the COMPLETE layer. OUT_OF_SCOPE and INCOMPLETE show none.

## 2. Scope profile
Identity is exact canonical (0a section 3 canonicalization), no article stripping: "a robin" and "robin" are different identities.
In scope (stored predicate names as in the engine):
- `is-a`: positive and `not-is-a`, over the is-a chain.
- `has`: positive and `not-has`, with inheritance down is-a.
- `is-in`: direct edge plus positive transitive chaining over is-in edges only. No negation, no is-a inheritance. Asked negative is-in: OUT_OF_SCOPE `negation_unsupported`.
- `means`: direct stored edge only, positive only (no chaining). Asked negative: `negation_unsupported`.
OUT_OF_SCOPE `predicate_unsupported`: can, uses, produces, needs, causes, anything else. Negation is valid only for is-a and has. Phrase mapping ("is" to is-a) belongs to the A24.1 parser adapter; the view takes structured (subject, predicate, object, polarity).
No `_RULES` proofs exist in 0b. Structural is-a inheritance and is-in chaining ARE derived evidence (section 4) but are not rule-based proof and carry no guards. The guard-blocked note (F4) is RESERVED, not emitted. Future conditions: current query and path only, a guard actually blocked a candidate path AND a complete strict search found no proof for that exact proposition and polarity, naming the grounded intermediate subject, never evidence or status, never from stale `gfail`.
Hypotheses, explore assumptions, `_derive_render` and cooc hints are never read.

## 3. Resolution, identity safety, no stripped lookups
- Subject resolution (0a): exact canonical key, or exact taught alias whose target key exists. NONE / UNIQUE / AMBIGUOUS; dangling aliases ignored; no fuzzy or reading-based resolution. Done in the view before any search.
- The production view MUST NOT use any article-stripped key, bucket or lookup (including the engine's article-stripped relation index as a lookup key). Edge subjects and objects are read as stored tuples and compared by exact canonical string. If the only available store is keyed by stripped subject, enumerating stored tuples is allowed only under the W counter (every tuple read counts); an exact-keyed index would be a core change needing its own consult (open question Q1).
- Collision scan covers ALL identities the view inspects: the asked subject and object, every endpoint (subject and object) of every inspected edge of either polarity, every alias key and alias target consulted during resolution, and endpoints of built-in definitions when means or built-ins are consulted. If two distinct canonical strings in that set share an article-stripped form (leading "a " or "an "), the result is OUT_OF_SCOPE `identity_collision` with no evidence and no named strings. The scan runs before COMPLETE is declared; a collision found at any point voids partial results.

## 4. Search semantics and evidence polarity (B1, B7)
Query-relative polarity. For asked (S, P, O, polarity pol): evidence whose stored polarity equals pol SUPPORTS the claim; evidence of the opposite polarity is OPPOSITION. This holds for is-a and has. Example: asked "S is-a O" with only a stored not-is-a: opposition, CONTRADICTED opposition_only. Asked "S not-is-a O" with the same store: support, SUPPORTED. Same-level evidence of both polarities gives CONTRADICTED both_sides. The truth table is 0a section 4 with P = support set and N = opposition set.
Levels. Level 0 = edges stored on the subject. Level k = nodes first reached by k is-a hops from the subject (shortest path, visited set).
- is-a: an edge from a node at level k-1 into O is evidence at level k.
- has: a `has` / `not-has` edge for O on a node at level k is evidence at level k.
- is-in: positive chain support only (BFS over is-in edges).
- means: direct only, level 0.
Nearest level: the smallest level holding evidence of either polarity. Show ALL evidence at that level in both polarities (caps as 0a). Deeper evidence is ignored and not reported. Output says: "nearest-level result, not an inventory of every reachable edge". Same-level order independence: result and ordering do not depend on insertion order.
Provenance: stored = a single stored tuple that directly states the asked claim: level-0 has/means, a direct is-a edge from the subject (level 1), a direct is-in edge. derived (structural) = anything needing an is-a hop for inheritance or two or more edges (is-a chain beyond one edge, inherited has, is-in chain). Derived evidence is dependent on every edge in its path, is never corroboration, and is distinct from `_RULES`-based proof. A subject reached via an alias keeps its provenance but notes alias resolution.

## 5. Completeness and bounds (B2, B3, B4, B8)
Own search, not `_rule_prove`, `pseen`, `memo` or first-result paths. Bounds (version 1, configured values): D=8, W=500.
- D bounds is-a traversal and has inheritance: only levels 0..8 are examined. An is-a object 9 hops away is INCOMPLETE `depth_limit`. Positive is-in chaining is not depth-bound: it is bounded by W and the visited set only.
- W is one shared counter per view over ALL phases and BOTH polarities: alias-table entries consulted in resolution, every stored tuple read during search (each tuple read counts once per read; repeat reads count again; the specified algorithm reads each node's tuple list once, classifying both polarities in the same pass), and built-in definitions consulted. Collision checks reuse endpoints of already-read items and add no count. Exactly 500 examinations are allowed. The 501st attempted examination stops the search: INCOMPLETE `work_limit`, even if some evidence was already seen.
- NONE subject resolution: COMPLETE UNKNOWN `no_trusted_evidence`, no search. AMBIGUOUS subject: COMPLETE AMBIGUOUS `ambiguous_subject`, candidates from taught keys and aliases only, no search, no evidence. Resolution counts toward W (alias entries read); a W overrun there is INCOMPLETE.
- Evidence found at nearest level k: COMPLETE iff every node at levels 0..k was fully read and both polarities of all evidence at level k enumerated and classified within D and W. No deeper search is required, and a remaining deeper frontier does not block COMPLETE.
- No evidence: COMPLETE UNKNOWN only if the reachable closure is exhausted (frontier empty) within D and W. A frontier remaining past level D: INCOMPLETE `depth_limit`. W exceeded: INCOMPLETE `work_limit`.
- If a limit prevents enumerating the opposite polarity or all same-level evidence, the result is INCOMPLETE and NO partial support or opposition is shown.
- Cycles are cut by the visited set and never cause INCOMPLETE by themselves.
- Display caps (5/5/5, root 0, display depth 2, 20 nodes) are rendering caps, distinct from the internal search depth, and never decide completeness.

## 6. Purity and reading isolation (F6, B6)
The view writes nothing: no `_derive_render`, no hypothesis records, no counters or caches. Engine calls used in tests run on an isolated deep copy with mode forced strict and leave original state byte-identical (repeatability test).
No reading-state access before COMPLETE is decided: `state["readings"]` and the exclusion input are not read, parsed or validated during resolution, search, collision scan or while computing INCOMPLETE/OUT_OF_SCOPE. Only after the layer is COMPLETE does the 0a privacy pipeline run (exclusion shape check, eligibility, order, cap, render). A test uses a poisoned readings store that fails on any access in INCOMPLETE and OUT_OF_SCOPE cases.

## 7. Built-in provenance (F8)
`_BUILTIN_RELS` means definitions appear with provenance `builtin`: "built-in definition; not user-taught; not independent evidence". Ordinary forget never removes them. A built-in plus a taught edge for the same claim are two displayed lines but never corroboration or two independent sources.

## 8. Versioning, fixtures, required tests
New files only: this contract and `tests/claimview/fixtures-0b.json` (expectations derived from the contract, not copied from engine output). caps v1 unchanged. The 39 real-core scenarios feed Oracle differentials on collision-free in-scope cases only.
Required test families before any implementation claim: per-predicate and polarity in/out of scope; query-relative polarity for is-a and has; NONE and AMBIGUOUS completeness; nearest-level plus same-level both polarities and insertion-order independence; 500 vs 501 examinations and shared counter across phases and polarities; is-a 8/9/10 hops vs is-in long chain; has at level 8 vs 9; one polarity limited; terminal-object, endpoint and alias collisions; no stripped lookups; strict-copy isolation and no mutation of any state; no reading access before COMPLETE; builtin provenance and forget; stored vs derived provenance; privacy exclusion and malformed exclusion (0a); interp/native differentials incl. non-ASCII; ordinary replies and 7-route corpus byte-identical; no new user-facing route.

## 9. Open implementation question
Q1: the engine's relation index is keyed by article-stripped subject. A view that bans stripped lookups must enumerate tuples (W-bounded, may hit INCOMPLETE on large memories) or wait for an exact-keyed index (core change plus oracle mirror, separate consult). The Python Oracle is unaffected (it holds its own exact store).
