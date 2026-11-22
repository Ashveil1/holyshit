"""DRAFT independent Oracle for claim view contract claimview-0b (rev 14).

ORACLE SELF-CONFORMANCE ARTIFACT ONLY. Written from agent/CLAIM_VIEW_CONTRACT_0B.md
alone. It is not a wrapper of ref_claim_view.py, it imports nothing from the
agent, and it reads no engine state. It proves nothing about any Holy
implementation: no production, parity or correctness claim. It holds its own
exact store, exact-keyed index and lifecycle model.

Pure per call: the only counter is the ephemeral W counter in one call.
"""

D = 8
W = 500
SUPPORT_CAP = 5
OPP_CAP = 5
REFERENCES = ("it", "this", "that", "he", "she", "they", "them", "those",
              "these", "one", "him", "her")
IN_SCOPE = ("is-a", "has", "is-in", "means")
NEG_OK = ("is-a", "has")
BUILTINS_DECL = (
    ("has", "the part relation: X has Y says Y is part of X"),
    ("is-a", "the kind relation: X is a Y says X is a kind of Y"),
    ("mean", "the definitional relation: X mean Y says the definition of X is Y"),
    ("is-in", "the containment relation: X is in Y says X is inside Y"),
)
_WS = " \t\n\r"
_UP = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class ImplementationError(Exception):
    """Index missing, stale or inconsistent: fail closed, no epistemic result."""


class _Stop(Exception):
    def __init__(self, layer, reason):
        Exception.__init__(self, layer + ":" + reason)
        self.layer, self.reason = layer, reason


def canon(s):
    out, ws = [], False
    for c in s:
        if c in _WS:
            ws = True
        else:
            if ws and out:
                out.append(" ")
            out.append(chr(ord(c) + 32) if c in _UP else c)
            ws = False
    return "".join(out)


def stripped(c):
    if c.startswith("a "):
        return c[2:]
    if c.startswith("an "):
        return c[3:]
    return c


def bkey(s):
    return s.encode("utf-8")


class Store:
    """Authoritative tuples + exact-keyed index + generation marker, mutated
    only through the methods below (one atomic path)."""

    def __init__(self):
        self._tuples = []          # (subject, pred, object, neg) originals
        self._index = {}           # canon(subject) -> [tuple, ...]
        self._gen = 0
        self._index_gen = 0
        self.fact_keys = []
        self.alias_records = []    # (alias, target)
        self._alias_by_key = {}
        self.builtins = []
        self.index_reads = 0
        self.alias_touched = []

    def _commit(self, tuples, index):
        self._tuples, self._index = tuples, index
        self._gen += 1
        self._index_gen = self._gen

    def add_tuple(self, t):
        t = tuple(t)
        index = {k: list(v) for k, v in (self._index or {}).items()}
        index.setdefault(canon(t[0]), []).append(t)
        self._commit(self._tuples + [t], index)

    def remove_tuple(self, t):
        t = tuple(t)
        if t not in self._tuples:
            return False
        tuples = list(self._tuples)
        tuples.remove(t)
        index = {k: list(v) for k, v in self._index.items()}
        index[canon(t[0])].remove(t)
        self._commit(tuples, index)
        return True

    def load(self, tuples):
        tuples = [tuple(t) for t in tuples]
        index = {}
        for t in tuples:
            index.setdefault(canon(t[0]), []).append(t)
        self._commit(tuples, index)

    def rebuild(self):
        self.load(self._tuples)

    def add_alias(self, alias, target):
        self.alias_records.append((alias, target))
        self._alias_by_key.setdefault(canon(alias), []).append((alias, target))

    # test-only fault injection, not a lifecycle path
    def _break(self, mode):
        if mode == "missing":
            self._index = None
        elif mode == "stale":
            self._gen += 1
        elif mode == "count":
            self._index = {k: list(v)[:-1] for k, v in self._index.items()}
        else:
            raise ValueError(mode)

    def add_explicit_empty_bucket(self, key):
        self._index.setdefault(key, [])

    def authoritative(self):
        return list(self._tuples)

    def full_index_equal(self):
        """Test helper: whole-index multiset compare, empty buckets inert."""
        if self._index is None:
            return False
        a = {}
        for t in self._tuples:
            a.setdefault(canon(t[0]), []).append(t)
        b = {k: v for k, v in self._index.items() if v}
        if set(a) != set(b):
            return False
        return all(sorted(a[k]) == sorted(b[k]) for k in a)

    # view-side reads (read-only)
    def check_integrity(self):
        if self._index is None:
            raise ImplementationError("index missing")
        if self._index_gen != self._gen:
            raise ImplementationError("generation mismatch")
        if sum(len(v) for v in self._index.values()) != len(self._tuples):
            raise ImplementationError("count mismatch")

    def bucket(self, key):
        self.index_reads += 1
        return self._index.get(key, [])

    def has_subject(self, key):
        return bool(self._index.get(key)) or key in {canon(k) for k in self.fact_keys}

    def alias_lookup(self, ckey):
        recs = self._alias_by_key.get(ckey, [])
        self.alias_touched.extend(recs)
        return list(recs)


class _Ctx:
    def __init__(self):
        self.w = 0
        self.seen = {}   # stripped form -> set of canon strings

    def identity(self, original):
        c = canon(original)
        s = self.seen.setdefault(stripped(c), set())
        s.add(c)
        if len(s) > 1:
            raise _Stop("OUT_OF_SCOPE", "identity_collision")

    def charge(self, *identities):
        if self.w >= W:
            raise _Stop("INCOMPLETE", "work_limit")
        self.w += 1
        for i in identities:
            self.identity(i)


def _order_key(t):
    # (predicate, polarity, canonical object, original object, original subject)
    return (bkey(t[1]), t[3], bkey(canon(t[2])), bkey(t[2]), bkey(t[0]))


def _oos(reason):
    return {"layer": "OUT_OF_SCOPE", "reason": reason}


def view(store, query, readings=None, exclusions=None):
    """query = (subject, predicate, object, neg). Returns a result dict, or
    raises ImplementationError. `readings`/`exclusions` are touched only
    after COMPLETE (never for AMBIGUOUS, INCOMPLETE, OUT_OF_SCOPE)."""
    s, p, o, neg = query
    neg = bool(neg)
    cs, co = canon(s), canon(o)
    if cs == "" or co == "" or cs in REFERENCES or co in REFERENCES:
        return _oos("shape_unsupported")
    if p not in IN_SCOPE:
        return _oos("predicate_unsupported")
    if neg and p not in NEG_OK:
        return _oos("negation_unsupported")
    store.check_integrity()
    ctx = _Ctx()
    try:
        ctx.identity(s)
        ctx.identity(o)
        kind, val = _resolve(store, ctx, s)
        if kind == "AMBIGUOUS":
            return {"layer": "COMPLETE", "status": "AMBIGUOUS",
                    "basis": "ambiguous_subject", "candidates": val[:5],
                    "w_charged": ctx.w}
        if kind == "NONE":
            res = {"layer": "COMPLETE", "status": "UNKNOWN",
                   "basis": "no_trusted_evidence"}
        else:
            res = _search(store, ctx, val, p, co, neg)
        res["w_charged"] = ctx.w
    except _Stop as e:
        return {"layer": e.layer, "reason": e.reason, "w_charged": ctx.w}
    if readings is not None:
        rows = _readings(readings, exclusions, cs, p, co)
        if rows:
            res["readings"] = rows[:5]
            res["readings_truncated"] = max(0, len(rows) - 5)
    return res


def _resolve(store, ctx, subject):
    c = canon(subject)
    targets = set()
    if store.has_subject(c):
        targets.add(c)
    recs = store.alias_lookup(c)
    recs.sort(key=lambda r: (bkey(canon(r[1])), bkey(r[0]), bkey(r[1])))
    for alias, target in recs:
        ctx.charge(alias, target)
        if store.has_subject(canon(target)):
            targets.add(canon(target))
    if len(targets) == 1:
        return "UNIQUE", next(iter(targets))
    if len(targets) > 1:
        return "AMBIGUOUS", sorted(targets, key=bkey)
    return "NONE", None


def _tkey(t):
    return (t[0], t[1], t[2], t[3])


def _dedupe(items):
    keys, out = set(), []
    for it in items:
        k = (it["prov"],) + tuple(it["path"])
        if k not in keys:
            keys.add(k)
            out.append(it)
    return out


def _prov(p, level, builtin):
    if builtin:
        return "builtin"
    if p == "means":
        return "stored"
    if p == "is-a":
        return "stored" if level == 1 else "derived"
    return "stored" if level == 0 else "derived"   # has, is-in


def _search(store, ctx, key, p, co, neg):
    support, oppose = [], []
    visited = {key}
    parent = {key: ()}
    frontier = [key]

    def examine(node):
        for t in sorted(store.bucket(node), key=_order_key):
            ctx.charge(t[0], t[2])
            yield t

    def add_ev(t, node, level, builtin=False):
        item = {"prov": _prov(p, level, builtin), "level": level,
                "path": parent[node] + (_tkey(t),)}
        (support if t[3] == neg else oppose).append(item)

    def finish(level):
        sup, opp = _dedupe(support), _dedupe(oppose)
        if sup and opp:
            st, basis = "CONTRADICTED", "both_sides"
        elif sup:
            st = "SUPPORTED"
            basis = ("derived_only" if all(i["prov"] == "derived" for i in sup)
                     else "support_only")
        else:
            st, basis = "CONTRADICTED", "opposition_only"
        provs = sorted({i["prov"] for i in sup + opp})
        r = {"layer": "COMPLETE", "status": st, "basis": basis,
             "level": level, "provenances": provs, "lines": len(sup) + len(opp),
             "support": sup[:SUPPORT_CAP], "opposition": opp[:OPP_CAP],
             "truncated": {"support": max(0, len(sup) - SUPPORT_CAP),
                           "opposition": max(0, len(opp) - OPP_CAP)}}
        if len(provs) == 1:
            r["provenance"] = provs[0]
        return r

    def unknown():
        return {"layer": "COMPLETE", "status": "UNKNOWN",
                "basis": "no_trusted_evidence"}

    def next_level(nxt):
        for k in nxt:
            visited.add(k)
        return list(nxt)

    if p == "is-a":
        for d in range(D + 1):
            nxt, boundary = {}, d == D
            for node in sorted(frontier, key=bkey):
                for t in examine(node):
                    if t[1] != "is-a":
                        continue
                    tc = canon(t[2])
                    if boundary:
                        if (not t[3] and tc not in visited) or (t[3] and tc == co):
                            raise _Stop("INCOMPLETE", "depth_limit")
                        continue
                    if tc == co:
                        add_ev(t, node, d + 1)
                    if not t[3] and tc not in visited and tc not in nxt:
                        nxt[tc] = None
                        parent[tc] = parent[node] + (_tkey(t),)
            if support or oppose:
                return finish(d + 1)
            if boundary:
                return unknown()
            frontier = next_level(nxt)
            if not frontier:
                return unknown()
        return unknown()
    if p == "has":
        for d in range(D + 1):
            nxt, deeper = {}, False
            for node in sorted(frontier, key=bkey):
                for t in examine(node):
                    if t[1] == "has" and canon(t[2]) == co:
                        add_ev(t, node, d)
                    elif t[1] == "is-a" and not t[3]:
                        tc = canon(t[2])
                        if tc not in visited:
                            if d == D:
                                deeper = True
                            elif tc not in nxt:
                                nxt[tc] = None
                                parent[tc] = parent[node] + (_tkey(t),)
            if support or oppose:
                return finish(d)
            if d == D:
                if deeper:
                    raise _Stop("INCOMPLETE", "depth_limit")
                return unknown()
            frontier = next_level(nxt)
            if not frontier:
                return unknown()
        return unknown()
    if p == "is-in":
        level = 0
        while frontier:
            nxt = {}
            for node in sorted(frontier, key=bkey):
                for t in examine(node):
                    if t[1] != "is-in" or t[3]:
                        continue
                    tc = canon(t[2])
                    if tc == co:
                        add_ev(t, node, level)
                    elif tc not in visited and tc not in nxt:
                        nxt[tc] = None
                        parent[tc] = parent[node] + (_tkey(t),)
            if support:
                return finish(level)
            frontier = next_level(nxt)
            level += 1
        return unknown()
    # means: direct taught tuples, then built-ins, no chaining
    for t in examine(key):
        if t[1] == "means" and not t[3] and canon(t[2]) == co:
            add_ev(t, key, 0)
    for bs, bo in sorted(store.builtins,
                         key=lambda b: _order_key((b[0], "means", b[1], False))):
        ctx.charge(bs, bo)
        if canon(bs) == key and canon(bo) == co:
            add_ev((bs, "means", bo, False), key, 0, builtin=True)
    if support:
        return finish(0)
    return unknown()


def _readings(readings, exclusions, cs, p, co):
    ex = exclusions if exclusions is not None else {"version": 1, "sources": []}
    if not isinstance(ex, dict) or ex.get("version") != 1 or \
            not isinstance(ex.get("sources"), list) or \
            any((not isinstance(x, str)) or x == "" for x in ex["sources"]):
        return []
    sources = set(ex["sources"])
    rows = []
    for r in readings:
        if not (canon(r["s"]) == cs and r["p"] == p and canon(r["o"]) == co):
            continue
        if r["source"] == "" or r["source"] in sources:
            continue
        sides = r.get("sides") or [r.get("side", "pos")]
        for side in sides:
            rows.append({"source": r["source"], "sentence": r.get("sentence", ""),
                         "side": side,
                         "label": "unverified reading, not used for the answer"})
    rows.sort(key=lambda x: (x["source"], x["sentence"], x["side"]))
    return rows
