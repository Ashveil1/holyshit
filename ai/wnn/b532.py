"""B-532 (connectome arm 2): is graph WIRING behaviorally distinct from isomorphic tables?
Same relational corpus stored as (G) edge graph + traversal and (T) relation tables + joins;
identical designed query frames for both; SHAM-G = degree-preserving rewired graph, same code.
Query frame (DESIGNED, named): '<start> r1 ... rk ?' forward, '? r1 ... rk <end>' reverse.
LEDGER pre-reg 2026-10-25."""
import random, json
import cur7 as C
from collections import defaultdict

# DESIGNED relational corpus (named as designed): (subj, rel, obj)
FACTS = [('นก', 'กิน', 'หนอน'), ('หนอน', 'อาศัย', 'ดิน'), ('ดิน', 'อยู่', 'สวน'),
         ('แมว', 'กิน', 'นก'), ('แมว', 'กิน', 'ปลา'), ('ปลา', 'อาศัย', 'น้ำ'),
         ('น้ำ', 'อยู่', 'บ่อ'), ('หนอน', 'กิน', 'ใบไม้'), ('ใบไม้', 'อยู่', 'ต้นไม้'),
         ('งู', 'กิน', 'นก')]
# ground truth, worked out by hand from FACTS
QUERIES = [
    ('นก กิน ?', {'หนอน'}), ('แมว กิน ?', {'นก', 'ปลา'}), ('หนอน กิน ?', {'ใบไม้'}),
    ('ปลา อาศัย ?', {'น้ำ'}), ('? กิน นก', {'แมว', 'งู'}), ('? กิน หนอน', {'นก'}),
    ('นก กิน อาศัย ?', {'ดิน'}), ('แมว กิน อาศัย ?', {'น้ำ'}), ('หนอน กิน อยู่ ?', {'ต้นไม้'}),
    ('? กิน อาศัย ดิน', {'นก'}), ('? กิน อาศัย น้ำ', {'แมว'}),
    ('แมว กิน อาศัย อยู่ ?', {'บ่อ'}), ('? กิน อาศัย อยู่ สวน', {'นก'}),
]

def parse(q):
    t = q.split()
    if t[0] == '?': return ('rev', t[-1], tuple(t[1:-1]))
    return ('fwd', t[0], tuple(t[1:-1]))

class Graph:
    """(G) explicit edges, adjacency traversal."""
    def __init__(self, facts):
        self.fwd = defaultdict(set); self.rev = defaultdict(set)
        for s, r, o in facts:
            self.fwd[(s, r)].add(o); self.rev[(o, r)].add(s)
        self.visits = 0
    def query(self, q):
        self.visits = 0
        direction, anchor, path = parse(q)
        adj = self.fwd if direction == 'fwd' else self.rev
        cur = {anchor}
        for r in (reversed(path) if direction == 'rev' else path):
            nxt = set()
            for e in cur:
                self.visits += 1
                nxt |= adj[(e, r)]
            cur = nxt
        return cur

class Tables:
    """(T) relation tables + designed joins (isomorphic store)."""
    def __init__(self, facts):
        self.rel = defaultdict(set)
        for s, r, o in facts:
            self.rel[r].add((s, o))
        self.visits = 0
    def query(self, q):
        self.visits = 0
        direction, anchor, path = parse(q)
        cur = {anchor}
        for r in (reversed(path) if direction == 'rev' else path):
            nxt = set()
            for s, o in self.rel[r]:
                self.visits += 1
                if direction == 'fwd' and s in cur: nxt.add(o)
                if direction == 'rev' and o in cur: nxt.add(s)
            cur = nxt
        return cur

def sham_facts(seed):
    """Degree-preserving rewire: permute objects within each relation."""
    rng = random.Random(seed)
    by_rel = defaultdict(list)
    for s, r, o in FACTS: by_rel[r].append((s, o))
    out = []
    for r, pairs in by_rel.items():
        objs = [o for _, o in pairs]; rng.shuffle(objs)
        out += [(s, r, o) for (s, _), o in zip(pairs, objs)]
    return out

def run_battery():
    out = {}
    G, T = Graph(FACTS), Tables(FACTS)
    mism, g_ans = [], {}
    for q, truth in QUERIES:
        ga, ta = G.query(q), T.query(q)
        g_ans[q] = sorted(ga)
        if ga != truth: mism.append(('G-truth', q, sorted(ga), sorted(truth)))
        if ta != truth: mism.append(('T-truth', q, sorted(ta), sorted(truth)))
        if ga != ta: mism.append(('G-T', q, sorted(ga), sorted(ta)))
    out['c1_mismatches'] = mism
    out['c1_identical'] = not mism
    # C2 sham overlap (Jaccard vs truth), 5 rewirings
    overlaps = []
    for sd in range(5):
        SG = Graph(sham_facts(100 + sd))
        for q, truth in QUERIES:
            sa = SG.query(q)
            overlaps.append(len(sa & truth) / len(sa | truth) if (sa | truth) else 1.0)
    out['c2_sham_mean_jaccard'] = round(sum(overlaps) / len(overlaps), 4)
    # C3 cost per arm (total visits over all queries)
    Gv = 0; Tv = 0
    for q, _ in QUERIES:
        G.query(q); Gv += G.visits
        T.query(q); Tv += T.visits
    out['c3_visits'] = {'graph': Gv, 'tables': Tv}
    # C4 existing battery + skill path spot check
    import random as _r
    from b521 import gen_corpus
    from b526 import CountBackend, battery
    from b527 import HSMLMemory, derive_skills, load_logged, SKILLS
    from cur7 import gen as cgen
    cb = CountBackend()
    for s in gen_corpus(_r.Random(0), 8): cb.observe(s.split())
    b = battery(cb)
    out['c4_attr_battery'] = {k: f'{v[0]}/{v[1]}' for k, v in b.items()}
    # LIB pinning (same logic as cur7.search) - skill programs may call pinned primitives;
    # depends on /tmp/c7_prog_0_base.json (TODO: repo-backed pinning, LEDGER Amendment 1)
    import os as _os, json as _json
    sv0 = '/tmp/c7_prog_0_base.json'
    if _os.path.exists(sv0):
        saved0 = _json.load(open(sv0))
        def tup0(e): return tuple(tup0(t) for t in e) if isinstance(e, list) else e
        for t0 in ('mod', 'mul', 'div', 'power', 'gcd', 'max', 'min'):
            if t0 in saved0:
                C.LIB[t0] = (lambda ff: (lambda a, b: ff(a, b)))(C.make_fn(tup0(saved0[t0])))
    mem = HSMLMemory(); mem.skills = derive_skills(load_logged())
    te = _r.Random(1000); okc = n = 0
    for task in SKILLS:
        for sc in (1, 2, 3, 4):
            for _ in range(10):
                x, y, r = cgen(task, te, sc)
                ans = mem.answer(f'{SKILLS[task]} ของ {x} คืออะไร')
                n += 1; okc += (ans.get('kind') == 'skill_answer' and ans.get('result') == r)
    out['c4_skill_spot'] = f'{okc}/{n}'
    return out

if __name__ == '__main__':
    out = run_battery()
    c1 = out['c1_identical']
    c2 = (1.0 - out['c2_sham_mean_jaccard']) >= 0.5  # Amendment 1: margin criterion
    c4 = all(v.split('/')[0] == v.split('/')[1] for v in out['c4_attr_battery'].values()) and out['c4_skill_spot'] == '160/160'
    verdict = 'PASS-NULL' if (c1 and c2 and c4) else 'FAIL'
    print(json.dumps({'verdict': verdict, 'c1': c1, 'c2': c2, 'c4': c4, **out}, ensure_ascii=False), flush=True)
    print('DONE', flush=True)
