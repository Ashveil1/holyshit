"""A24.0a reference model for the claim view (contract claimview-0a).

SPEC ARTIFACT ONLY. This is a Python model of the contract in
agent/CLAIM_VIEW_CONTRACT.md. It is not the core implementation, it does
not prove that a later Holy implementation is correct, and nothing in the
agent imports it. It abstracts the core's inheritance rules into one
small rule family so the contract's edge cases can be pinned down and
shared with the later Oracle as fixtures.

Pure and read-only: the state and the exclusion input are never mutated
(tests deepcopy-compare). No clock, no randomness, no I/O.
"""

CONTRACT = "claimview-0a"
CAPS = {"version": 1, "support": 5, "opposition": 5, "readings": 5,
        "candidates": 5, "depth": 2, "nodes": 20}
ASSERTION = ("stored fact in current memory; original wording and time are "
             "not retained")
DERIVED = ("derived by rule from stored facts; premises are not independent "
           "corroboration")
IDENTITY = "not independently authenticated"
QUALITY = "evidence quality not assessed"
READING = "unverified reading, not used for the answer"
UNKNOWN_TEXT = "no matching trusted support in current view"
LABELS = {"assertion": ASSERTION, "identity": IDENTITY, "quality": QUALITY}
REFERENCES = ["it", "this", "that", "he", "she", "they", "them", "those",
              "these", "one", "him", "her"]
PHRASES = {"is": ("is", "is not"), "has": ("has", "does not have"),
           "in": ("is in", "is not in")}
# Guard: (predicate, kind) pairs. A rule may not carry predicate p to a
# subject that is-a kind. A guard stop is a NOTE, never evidence.
WS = " \t\n\r"
UP = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def canon(s):
    """Collapse ASCII whitespace runs, trim, lowercase ASCII letters only.
    No Unicode normalization (NFC/NFD are NOT folded), no case folding of
    non-ASCII, no stemming."""
    if not isinstance(s, str):
        return None
    out, ws = [], False
    for c in s:
        if c in WS:
            ws = True
        else:
            if ws and out:
                out.append(" ")
            out.append(chr(ord(c) + 32) if c in UP else c)
            ws = False
    return "".join(out)


def resolve(state, subject):
    """Exact canonical key or exact taught alias, existing targets only.
    Returns ('UNIQUE', key) | ('AMBIGUOUS', [keys sorted]) | ('NONE', None).
    Readings never resolve a subject."""
    c = canon(subject)
    hits = set()
    if c is None or c == "":
        return ("NONE", None)
    for k in state.get("facts", {}):
        if canon(k) == c:
            hits.add(k)
    for a, t in state.get("aliases", {}).items():
        if canon(a) == c and t in state.get("facts", {}):
            hits.add(t)
    if len(hits) == 1:
        return ("UNIQUE", sorted(hits)[0])
    if len(hits) > 1:
        return ("AMBIGUOUS", sorted(hits))
    return ("NONE", None)


def valid_exclusions(ex):
    """Fail closed: anything but {'version': 1, 'sources': [str, ...]} is
    malformed (returns None)."""
    if not isinstance(ex, dict) or ex.get("version") != 1:
        return None
    src = ex.get("sources")
    if not isinstance(src, list):
        return None
    for x in src:
        if not isinstance(x, str) or x == "":
            return None
    return set(src)


def phrase(s, p, o, neg):
    if p in PHRASES:
        return "%s %s %s" % (s, PHRASES[p][1 if neg else 0], o)
    return "%s %s%s %s" % (s, "not-" if neg else "", p, o)


def _edges(state, s, p, o, neg):
    want = ("not-" + p) if neg else p
    for e in state.get("rels", []):
        if canon(e[0]) == canon(s) and e[1] == want and canon(e[2]) == canon(o):
            return True
    return False


def _isa_targets(state, s):
    out = set()
    for e in state.get("rels", []):
        if canon(e[0]) == canon(s) and e[1] == "is":
            out.add(canon(e[2]))
    return sorted(out)


class _Budget:
    def __init__(self):
        self.nodes = 0
        self.truncated = False
        self.blocked = []


def _prove(state, s, p, o, neg, path, depth, bud):
    """Return a list of proofs (items). Direct taught edge first, then the
    single rule family: X p Y if X is Z (taught) and Z p Y (provable).
    Cycles are cut (that branch is not a proof). Depth 0 is the root, and
    premises at depth > CAPS['depth'] are not expanded (truncated)."""
    key = (canon(s), p, canon(o), neg)
    if key in path:
        return []
    bud.nodes += 1
    if bud.nodes > CAPS["nodes"]:
        bud.truncated = True
        return []
    if _edges(state, s, p, o, neg):
        return [{"kind": "relation_edge", "text": phrase(s, p, o, neg),
                 "premises": []}]
    if depth >= CAPS["depth"]:
        # a rule could apply deeper; say so instead of silently stopping
        if _isa_targets(state, s):
            bud.truncated = True
        return []
    proofs = []
    for z in _isa_targets(state, s):
        if z == canon(s) or (z, p, canon(o), neg) in path:
            continue
        guard = [g for g in state.get("guards", [])
                 if g[0] == p and canon(g[1]) == z]
        if guard:
            bud.blocked.append("rule blocked by guard: %s cannot carry "
                               "'%s' to %s" % (z, p, canon(s)))
            continue
        prem1 = {"kind": "relation_edge", "text": phrase(s, "is", z, False),
                 "premises": []}
        sub = _prove(state, z, p, o, neg, path | {key}, depth + 1, bud)
        for sp in sub:
            proofs.append({"kind": "derived_rule",
                           "text": phrase(s, p, o, neg),
                           "rule": "inherit-via-is",
                           "premises": [prem1, sp]})
    return proofs


def _sorted_items(items):
    return sorted(items, key=lambda i: (i["kind"], i["text"], i.get("rule", "")))


def view(state, query, exclusions):
    """query: {'propositions': [{'s','p','o','neg'}, ...]}
    Pipeline (fixed): resolve -> eligibility -> order -> cap -> output."""
    props = query.get("propositions", [])
    base = {"contract": CONTRACT, "caps": dict(CAPS), "labels": dict(LABELS)}
    if len(props) == 0:
        return dict(base, status="REFUSED", reason="no proposition")
    first = props[0]
    if canon(first["s"]) in REFERENCES or canon(first["o"]) in REFERENCES:
        return dict(base, status="REFUSED",
                    reason="reference words are not resolved; restate the "
                           "full proposition")
    if len(props) > 1:
        cands = sorted({phrase(q["s"], q["p"], q["o"], q.get("neg", False))
                        for q in props})
        return dict(base, status="OK", resolution="UNIQUE",
                    epistemic="AMBIGUOUS", basis="ambiguous_proposition",
                    candidates=cands[:CAPS["candidates"]],
                    truncated={"candidates": max(0, len(cands) - CAPS["candidates"])},
                    support=[], opposition=[], derivations_blocked=[])
    q = first
    neg = bool(q.get("neg", False))
    kind, val = resolve(state, q["s"])
    if kind == "NONE":
        return dict(base, status="OK", resolution="NONE", epistemic="UNKNOWN",
                    basis="no_trusted_evidence", text=UNKNOWN_TEXT,
                    support=[], opposition=[], derivations_blocked=[],
                    **_readings_part(state, q, exclusions, False))
    if kind == "AMBIGUOUS":
        return dict(base, status="OK", resolution="AMBIGUOUS",
                    epistemic="AMBIGUOUS", basis="ambiguous_subject",
                    candidates=val[:CAPS["candidates"]],
                    truncated={"candidates": max(0, len(val) - CAPS["candidates"])},
                    support=[], opposition=[], derivations_blocked=[])
    s = val
    bud = _Budget()
    pos = _prove(state, s, q["p"], q["o"], neg, frozenset(), 0, bud)
    opp = _prove(state, s, q["p"], q["o"], not neg, frozenset(), 0, bud)
    pos, opp = _sorted_items(pos), _sorted_items(opp)
    n_pos, n_opp = len(pos), len(opp)
    if n_pos and n_opp:
        ep, basis = "CONTRADICTED", "both_sides"
    elif n_pos:
        ep = "SUPPORTED"
        basis = ("support_only" if any(i["kind"] == "relation_edge"
                                       for i in pos) else "derived_only")
    elif n_opp:
        ep, basis = "CONTRADICTED", "opposition_only"
    else:
        ep, basis = "UNKNOWN", "no_trusted_evidence"
    out = dict(base, status="OK", resolution="UNIQUE", epistemic=ep,
               basis=basis, support=pos[:CAPS["support"]],
               opposition=opp[:CAPS["opposition"]],
               truncated={"support": max(0, n_pos - CAPS["support"]),
                          "opposition": max(0, n_opp - CAPS["opposition"]),
                          "derivation_nodes": bud.truncated},
               derivations_blocked=sorted(set(bud.blocked)))
    if ep == "UNKNOWN":
        out["text"] = UNKNOWN_TEXT
    out.update(_readings_part(state, q, exclusions, True))
    return out


def _readings_part(state, q, exclusions, _unique):
    """Readings never affect status. Fail closed: with a missing or
    malformed exclusion input the section is ABSENT (silent), identical
    to a state without readings. Eligibility runs before order, cap and
    count; there is no 'N hidden' anywhere."""
    ex = valid_exclusions(exclusions)
    if ex is None:
        return {}
    rows = []
    for r in state.get("readings", []):
        if not (canon(r.get("s")) == canon(q["s"]) and r.get("p") == q["p"]
                and canon(r.get("o")) == canon(q["o"])):
            continue
        for side in ("pos", "neg"):
            for ent in r.get(side, []):
                src, sent = ent
                if not isinstance(src, str) or src == "" or src in ex:
                    continue
                rows.append({"source": src, "sentence": sent, "side": side,
                             "marker": r.get("marker", "") or None,
                             "label": READING})
    rows.sort(key=lambda x: (x["source"], x["sentence"], x["side"]))
    if not rows:
        return {}
    return {"readings": rows[:CAPS["readings"]],
            "readings_truncated": max(0, len(rows) - CAPS["readings"])}
