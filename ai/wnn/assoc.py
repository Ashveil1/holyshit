"""B-558: bounded associative layer over the live structured store (route A,
Ash-approved 2026-10-26; pre-registered in LEDGER). Integer count tables over
char n-grams (wnn heritage: no floats, no gradients, CPU-cheap). Fed ONLY by
facts the structured store accepted; the store stays the single source of
truth and this index is a pure derived view — rebuilt from the store after any
mutation, so retraction is exact by construction (no separate unlearn path to
trust). Proposals are re-verified against live memory before they may be
spoken (B-548 philosophy). Designed mechanism; named limits, not learning
claims beyond the measured axes.

Mechanism (named, not 'understanding'): NAME-ANCHORED coverage. The layer
knows the surfaces of taught names (incl. linked EN surfaces). A sentence
proposes the taught name whose surface n-grams it covers best; among that
name's facts it prefers those whose attr surfaces also appear. Question-word
grams score nothing because they occur in no fact — phrasing variation is
absorbed instead of parsed."""

def _ngrams(s, ns=(2, 3, 4, 5)):
    """Distinct char n-grams of the space-stripped lowered surface. Thai has no
    word boundaries; char n-grams are the tokenizer-free feature (named choice).
    n=2 included so 2-char names still produce features."""
    t = s.replace(' ', '').lower()
    out = set()
    for n in ns:
        for i in range(len(t) - n + 1):
            out.add(t[i:i + n])
    return out

def _strip(s):
    return s.replace(' ', '').lower()

class Assoc:
    def __init__(self):
        self.name_grams = {}   # name -> set(ngram)  (all surfaces of the name)
        self.facts = {}        # (name, attr) -> set(ngram) of attr surfaces
        self.total_records = 0

    def rebuild(self, name_surfaces, facts):
        """name_surfaces: {name: [surfaces]}; facts: {(name, attr): [attr surfaces]}.
        Replaces all state (pure derived view of the store)."""
        self.name_surfaces = {n: [_strip(t) for t in ts] for n, ts in name_surfaces.items()}
        self.facts = {f: [_ngrams(t) for t in ts] for f, ts in facts.items()}
        self.total_records = sum(len(v) for v in self.facts.values())

    def propose(self, sentence):
        """v3 frozen rule: NAME-EXACT anchoring - a taught name surface must appear
        VERBATIM (space-stripped, case-insensitive) in the sentence; the longest
        matched surface wins; a tie or no match -> abstain. N-gram coverage ranks
        only that name's attrs. Fuzzy name tolerance caused a dev-set fabrication
        (เบอร์ต proposed บอร์ท) and is out of scope for B-558 - recorded in LEDGER.
        Returns (name|None, ranked_fact_keys, diagnostics)."""
        q = _strip(sentence)
        if not q or not self.name_surfaces:
            return None, [], {}
        best = []  # (surface_len, name)
        for name, surfaces in self.name_surfaces.items():
            hit = max((len(t) for t in surfaces if t and t in q), default=0)
            if hit:
                best.append((hit, name))
        if not best:
            return None, [], {}
        best.sort(reverse=True)
        top_len, top_name = best[0]
        tied = [n for l, n in best if l == top_len]
        diag = {'matched_len': top_len, 'tied': len(tied)}
        if len(tied) > 1:
            return None, [], diag
        qg = _ngrams(sentence)
        scored = []
        for fact, surfaces in self.facts.items():
            if fact[0] != top_name:
                continue
            vals = [len(g & qg) / len(g) for g in surfaces if g]
            scored.append((max(vals) if vals else 0.0, fact))
        scored.sort(key=lambda t: -t[0])
        diag['attr_cov'] = scored[0][0] if scored else 0.0
        return top_name, [f for _c, f in scored], diag
