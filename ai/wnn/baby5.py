"""P29 (baby5.py): scaled baby - free conversation + unscripted situation stream, NO scene slots.
World: latent persistent THINGS (8 entities x 6 actions x 3 locations x 2 times) appear in the
situation stream as OPAQUE feature tokens (F0..F18) - persistent identity, no slot labels, no
semantics. Valid scenes sampled from world constraints (inanimates restricted). Per scene the baby
hears k=2..4 lines; each line is from pool A (here-and-now, about THIS scene) with prob f else
pool B (free conversation about anything). B lines heard during the scene = realistic dilution.
Learner: feature-token Hebbian association (word<->token, +1 present / -0.25 absent, as baby4)
- no slots, no clustering needed for grounding; token-class structure measured separately (P29b).
Chunk 1: world + mixer + TEMPLATE fallback pools (smoke test until LLM pools.json arrives) +
grounding accuracy vs dilution f. PRE-STAGED: C1 f=1.0 grounding >=.80; controls f=0 & shuffled <=.20."""
import random, json, sys
from collections import defaultdict
# --- world: 19 latent things, opaque tokens ---
ENT = ['mae', 'pho', 'maew', 'hma', 'ball', 'nom', 'khao', 'nok']
ACT = ['non', 'kin', 'wing', 'len', 'ma', 'pai']
LOC = ['ban', 'suan', 'rongrien']
TIM = ['chao', 'yen']
THINGS = [('E', e) for e in ENT] + [('A', a) for a in ACT] + [('L', l) for l in LOC] + [('T', t) for t in TIM]
TOK = {t: f'F{i}' for i, t in enumerate(THINGS)}          # harness-only mapping
TOKA = {v: k for k, v in TOK.items()}
ANIM = {'mae', 'pho', 'maew', 'hma', 'nok'}
VALID = [(e, a) for e in ENT for a in ACT if e in ANIM or a in ('len', 'ma')]
# Thai words for template fallback pools (LLM pools replace these)
WE = {'mae': 'แม่', 'pho': 'พ่อ', 'maew': 'แมว', 'hma': 'หมา', 'ball': 'ลูกบอล', 'nom': 'นม', 'khao': 'ข้าว', 'nok': 'นก'}
WA = {'non': 'นอน', 'kin': 'กิน', 'wing': 'วิ่ง', 'len': 'เล่น', 'ma': 'มา', 'pai': 'ไป'}
WL = {'ban': 'ที่บ้าน', 'suan': 'ที่สวน', 'rongrien': 'ที่โรงเรียน'}
FILL = ['จ๊ะ', 'ลูก', 'ดูสิ', 'นะ', 'ค่ะ', 'แล้ว', 'กำลัง', 'อยู่', 'ตรงนั้น']
FREE = ['วันนี้ อากาศ ร้อน มาก เลย', 'ข่าว เมื่อคืน น่าสนใจ จัง', 'พรุ่งนี้ ต้อง ไป ตลาด เช้า',
        'เลข สอง บวก สาม ได้ ห้า นะ', 'เรื่อง เมื่อวาน ตลก ดี', 'คืนนี้ ฝัน ดี นะ ลูก',
        'อาหาร เย็น นี้ อร่อย จัง', 'ประวัติ ศาสตร์ สนุก นะ', 'น้ำ หมด แล้ว ต้ม เพิ่ม',
        'โทรศัพท์ ดัง อีก แล้ว']
def template_pool_a(rng, e, a, l):
    w = [WE[e], WA[a], WL[l]]
    r = list(range(3)); rng.shuffle(r)
    line = [w[i] for i in r[:rng.choice((2, 3))]]
    return line + rng.sample(FILL, rng.choice((1, 2)))
def template_pool_b(rng):
    return rng.choice(FREE).split()
class World:
    def __init__(s, rng): s.rng = rng
    def scene(s):
        e, a = s.rng.choice(VALID); l = s.rng.choice(LOC); t = s.rng.choice(TIM)
        return (e, a, l, t)
    def tokens(s, sc): return {TOK[('E', sc[0])], TOK[('A', sc[1])], TOK[('L', sc[2])], TOK[('T', sc[3])]}
class Baby5:
    def __init__(s):
        s.assoc = defaultdict(lambda: defaultdict(float)); s.heard = 0
        s.tokcount = defaultdict(int)
    def hear(s, words, present):
        for w in words:
            s.heard += 1
            for tok in TOKA: s.assoc[w][tok] += 1.0 if tok in present else -0.25
        for tok in present: s.tokcount[tok] += 1
    def word_for(s, tok):
        best, bs = None, 0.5
        for w in s.assoc:
            sc = s.assoc[w][tok] - 0.5 * sum(s.assoc[w][o] for o in TOKA if o != tok)
            if sc > bs: best, bs = w, sc
        return best
    def best_tok(s, w):
        if w not in s.assoc: return None
        t, sc = max(s.assoc[w].items(), key=lambda kv: kv[1])
        tot = sum(max(0.0, v) for v in s.assoc[w].values())
        return t if sc > 0 and sc >= 1.5 * (tot - sc) else None
def run(seed, f, pool_a, pool_b, days=5, scenes_per_day=100, shuffle=False):
    rng = random.Random(2000 + seed); w = World(rng); b = Baby5()
    wr = random.Random(999) if shuffle else None
    for day in range(days):
        for _ in range(scenes_per_day):
            sc = w.scene(); pres = w.tokens(sc)
            for _ in range(rng.choice((2, 3, 4))):
                line = pool_a(rng, sc) if rng.random() < f else pool_b(rng)
                if shuffle: wr.shuffle(line)
                b.hear(line, pres)
    # grounding eval: for each thing, does word_for(token) recover the right Thai word?
    # harness-only mapping: entity tokens -> WE, action tokens -> WA (loc/time tokens unscored)
    ok, tot = 0, 0
    for e in ENT:
        tot += 1; ok += b.word_for(TOK[('E', e)]) == WE[e]
    for a in ACT:
        tot += 1; ok += b.word_for(TOK[('A', a)]) == WA[a]
    return ok, tot
if __name__ == '__main__':
    for f in (1.0, 0.5, 0.2, 0.0):
        accs = []
        for seed in range(5):
            ok, tot = run(seed, f, lambda r, sc: template_pool_a(r, sc[0], sc[1], sc[2]), template_pool_b)
            accs.append(ok / tot)
        print(f'f={f}: grounding {sum(accs)/len(accs):.2f} (per-seed {["%.2f"%a for a in accs]}, n={tot})', flush=True)

# --- chunk 2: P29b word-class discovery via mutual-exclusivity (word-word line co-occurrence) ---
def nmi(labels_true, labels_pred):
    import math
    n = len(labels_true); ct, cp = {}, {}
    joint = defaultdict(int)
    for t, p in zip(labels_true, labels_pred): ct[t] = ct.get(t, 0) + 1; cp[p] = cp.get(p, 0) + 1; joint[(t, p)] += 1
    mi = sum(v / n * math.log((v * n) / (ct[t] * cp[p])) for (t, p), v in joint.items())
    ht = -sum(c / n * math.log(c / n) for c in ct.values()); hp = -sum(c / n * math.log(c / n) for c in cp.values())
    return mi / ((ht + hp) / 2) if ht and hp else 0.0
class Baby5P(Baby5):
    def __init__(s):
        super().__init__()
        s.cooc = defaultdict(lambda: defaultdict(float))  # word-word line co-occurrence
        s.oc = defaultdict(int)                            # class-bigram order counts (inferred classes)
    def hear(s, words, present, wcls=None):
        super().hear(words, present)
        for w1 in words:
            for w2 in words:
                if w1 != w2: s.cooc[w1][w2] += 1.0
        if wcls:
            for w1, w2 in zip(words, words[1:]):
                c1, c2 = wcls.get(w1), wcls.get(w2)
                if c1 and c2 and c1 != c2: s.oc[(c1, c2)] += 1
def cluster_words(baby, words, k=4):
    """Agglomerative (average linkage, cosine) over co-occurrence ROWS: same-class words
    appear with the same partners and never with each other -> similar rows."""
    import math
    def row(w): return baby.cooc[w]
    def cos(a, b):
        dot = sum(v * b.get(t, 0.0) for t, v in a.items())
        na, nb = math.sqrt(sum(v * v for v in a.values())), math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0
    clusters = [[w] for w in words]
    while len(clusters) > k:
        bi, bj, bs = -1, -1, -2.0
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                sim = sum(cos(row(a), row(b)) for a in clusters[i] for b in clusters[j]) / (len(clusters[i]) * len(clusters[j]))
                if sim > bs: bi, bj, bs = i, j, sim
        clusters[bi] += clusters[bj]; del clusters[bj]
    return clusters
def label_clusters(baby, clusters):
    """Label a cluster E/A/L/T/? by mean positive association of its words to that class's tokens.
    (Class token SETS are harness structure; the learner only gets cluster ids. Labeling is for scoring
    and for the order channel, like baby4's best_tok.)"""
    cls_tokens = defaultdict(list)
    for tok, (c, _n) in TOKA.items(): cls_tokens[c].append(tok)
    wcls = {}
    for cl in clusters:
        scores = {}
        for c in ('E', 'A', 'L'):
            vals = []
            for w in cl:
                av = baby.assoc.get(w, {})
                vals.append(max((av.get(t, 0.0) for t in cls_tokens[c]), default=0.0))
            scores[c] = sum(vals) / max(1, len(vals))
        lab = max(scores, key=scores.get)
        if scores[lab] <= 0.05: lab = '?'
        for w in cl: wcls[w] = lab
    return wcls
def run2(seed, f, pool_a, pool_b, days=5, scenes_per_day=100, k=4):
    rng = random.Random(2000 + seed); w = World(rng); b = Baby5P()
    for day in range(days):
        for _ in range(scenes_per_day):
            sc = w.scene(); pres = w.tokens(sc)
            for _ in range(rng.choice((2, 3, 4))):
                b.hear(pool_a(rng, sc) if rng.random() < f else pool_b(rng), pres)
    true_cls = {}
    for wd in b.assoc:
        if wd in WE.values(): true_cls[wd] = 'E'
        elif wd in WA.values(): true_cls[wd] = 'A'
        elif wd in WL.values(): true_cls[wd] = 'L'
        elif wd in FILL: true_cls[wd] = 'P'
        else: true_cls[wd] = 'F'
    # score on words heard at least 5 times (enough signal), needing >=2 true classes present
    heard = [wd for wd in b.assoc if sum(b.cooc[wd].values()) >= 5]
    clusters = cluster_words(b, heard, k=k)
    pred = {}
    for ci, cl in enumerate(clusters):
        for wd in cl: pred[wd] = ci
    nmi_v = nmi([true_cls[wd] for wd in heard], [pred[wd] for wd in heard])
    wcls = label_clusters(b, clusters)
    for _ in range(scenes_per_day):
        sc = w.scene(); pres = w.tokens(sc)
        for _ in range(rng.choice((2, 3, 4))):
            b.hear(pool_a(rng, sc) if rng.random() < f else pool_b(rng), pres, wcls)
    ea = oc_ratio = None
    fwd, rev = b.oc.get(('E', 'A'), 0), b.oc.get(('A', 'E'), 0)
    ea = fwd + rev
    return nmi_v, len(heard), ea, wcls, clusters
if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'c2':
    for f in (1.0, 0.5, 0.2):
        for seed in range(3):
            nv, nw, ea, wcls, clusters = run2(seed, f, lambda r, sc: template_pool_a(r, sc[0], sc[1], sc[2]), template_pool_b)
            print(f'f={f} seed{seed}: NMI={nv:.3f} words={nw} EA-adj={ea} clusters={[len(c) for c in clusters]}', flush=True)

# --- chunk 3: LLM pools (blind writer pools.json) wiring ---
RWE = {v: k for k, v in WE.items()}; RWA = {v: k for k, v in WA.items()}
def load_llm_pools(path):
    d = json.load(open(path))
    covered = []
    for key in d['A']:
        e_th, a_th = key.split()
        covered.append((RWE[e_th], RWA[a_th]))
    def pool_a(rng, sc):
        e, a = sc[0], sc[1]
        return rng.choice(d['A'][f'{WE[e]} {WA[a]}']).split()
    def pool_b(rng):
        return rng.choice(d['B']).split()
    return pool_a, pool_b, covered
class WorldC(World):
    """World restricted to pool-covered (entity, action) pairs."""
    def __init__(s, rng, covered):
        super().__init__(rng); s.covered = covered
    def scene(s):
        e, a = s.rng.choice(s.covered)
        l = s.rng.choice(LOC); t = s.rng.choice(TIM)
        return (e, a, l, t)
def run_llm(seed, f, pool_a, pool_b, covered, days=5, scenes_per_day=100, shuffle=False):
    rng = random.Random(2000 + seed); w = WorldC(rng, covered); b = Baby5()
    wr = random.Random(999) if shuffle else None
    for day in range(days):
        for _ in range(scenes_per_day):
            sc = w.scene(); pres = w.tokens(sc)
            for _ in range(rng.choice((2, 3, 4))):
                line = pool_a(rng, sc) if rng.random() < f else pool_b(rng)
                if shuffle: wr.shuffle(line)
                b.hear(line, pres)
    ok, tot = 0, 0
    for e in ENT:
        tot += 1; ok += b.word_for(TOK[('E', e)]) == WE[e]
    for a in ACT:
        tot += 1; ok += b.word_for(TOK[('A', a)]) == WA[a]
    return ok, tot
if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'p29a':
    pa, pb, covered = load_llm_pools(sys.argv[2])
    print(f'covered scene types: {len(covered)}', flush=True)
    for f in (1.0, 0.5, 0.2, 0.1, 0.05, 0.0):
        accs = []
        for seed in range(5):
            ok, tot = run_llm(seed, f, pa, pb, covered)
            accs.append(ok / tot)
        print(f'f={f}: grounding {sum(accs)/len(accs):.2f} (per-seed {["%.2f"%a for a in accs]}, n={tot})', flush=True)
