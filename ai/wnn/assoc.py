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

# B-558 v4: finite designed claim/negation markers (named limit, same philosophy
# as B-544 GUARD_WORDS - NOT general intent understanding). Substring match on the
# stripped sentence because Thai glues words.
CLAIM_MARKERS = ('ไม่', 'หรอก', 'ใช่ไหม', 'มั้ย', 'ไหม', 'หรือเปล่า', 'จริง')

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
        # v4 (adversarial controls b558_adv): finite CLAIM/negation marker list -
        # if the sentence asserts/denies/questions a claim rather than asking about
        # an entity, the layer abstains (same named-limit philosophy as B-544's
        # guard list; a taught word containing a marker as substring blocks
        # proposals about it - recorded limit). Pure question softeners (มั้ง/น่าจะ)
        # are NOT blocked: dev evidence shows them in genuine questions.
        if any(m in q for m in CLAIM_MARKERS):
            return None, [], {'blocked': 'claim_marker'}
        # exact-substring anchoring with nesting resolution: a matched surface that
        # is itself a substring of another name's matched surface is dropped
        # (nested names), then >1 remaining distinct name -> abstain (single-entity
        # retrieval scope only - multi-entity questions are out of scope, named).
        matched = []  # (surface_len, surface, name)
        for name, surfaces in self.name_surfaces.items():
            hits = [t for t in surfaces if t and t in q]
            if hits:
                t = max(hits, key=len)
                matched.append((len(t), t, name))
        if not matched:
            return None, [], {}
        surviving = [(l, t, n) for l, t, n in matched
                     if not any(t != t2 and t in t2 for _l2, t2, _n2 in matched)]
        names_left = sorted({n for _l, _t, n in surviving})
        diag = {'matched': len(matched), 'entities': len(names_left)}
        if len(names_left) != 1:
            return None, [], diag
        top_name = names_left[0]
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
