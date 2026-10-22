import random, json, math, re
from collections import defaultdict
import text2prog2
from text2prog2 import TwoStep, run2, run_hyp, numbers_of, feats, HYP, H2, C1, C2, CONN, make
import text2prog as P

THAI = re.compile(r'[฀-๿]')
def th_only(frames): return [f for f in frames if THAI.search(f)]
TC1 = {o: th_only(fs[0]) for o, fs in C1.items()}
TC2 = {o: th_only(fs[0]) for o, fs in C2.items()}
TCONN = th_only(CONN[0])

def gen_th(rng, p_single=0.3):
    if rng.random() < p_single:
        op = rng.choice([o for o in TC1 if TC1[o]]); t, a = make(op, rng.choice(TC1[op]), rng, big=False)
        return ('single',), t, a
    o1 = rng.choice([o for o in TC1 if TC1[o]])
    t1, r1 = make(o1, rng.choice(TC1[o1]), rng, big=False)
    o2 = rng.choice([o for o in TC2 if TC2[o]])
    if o2 == 'fact':
        for _ in range(50):
            if r1 <= 8: break
            t1, r1 = make(o1, rng.choice(TC1[o1]), rng, big=False)
        if r1 > 8: return gen_th(rng, p_single)
    c = rng.randrange(2, 12)
    t2 = rng.choice(TC2[o2]).format(c=c)
    conn = rng.choice(TCONN)
    if o2 == 'add': r = r1 + c
    elif o2 == 'sub': r = r1 - c
    elif o2 == 'mul': r = r1 * c
    elif o2 == 'div': r = r1 // c
    elif o2 == 'fact': r = math.factorial(r1)
    else: r = P.isp(r1)
    return (o1, o2), (t1 + ' ' + conn + ' ' + t2).replace('  ', ' ').strip(), int(r)

class CharTwoStep:
    """TwoStep over character positions of space-stripped Thai; char n-gram features."""
    def __init__(s):
        s.A = P.Learner('char'); s.B = P.Learner('char'); s.bnd = defaultdict(lambda: [0.0, 0.0])
    def fit(s, rows):
        for text, ans in rows:
            t = text; n = len(t); E = []
            for h1 in HYP:
                if run_hyp(h1, numbers_of(t)) == ans: E.append((None, h1, None))
            for k in range(1, n):
                L_, R_ = t[:k], t[k:]
                for h1 in HYP:
                    for h2 in H2:
                        if run2(h1, h2, L_, R_) == ans: E.append((k, h1, h2))
            if any(k is None for k, _, _ in E): E = [e for e in E if e[0] is None]
            if not E: continue
            w = 1.0 / len(E)
            for k, h1, h2 in E:
                if k is None:
                    for f in feats(t, 'char'): s.A.tot[f] += w; s.A.cnt[f][h1] += w
                else:
                    L_, R_ = t[:k], t[k:]
                    for f in feats(L_, 'char'): s.A.tot[f] += w; s.A.cnt[f][h1] += w
                    for f in feats(R_, 'char'): s.B.tot[f] += w; s.B.cnt[f][h2] += w
            for k in range(1, n): s.bnd[(t[k - 1], t[k])][1] += 1
            for k, h1, h2 in E:
                if k is not None: s.bnd[(t[k - 1], t[k])][0] += w
            s.bnd['__single__'][0] += sum(w for k, _, _ in E if k is None)
        s.nsent = len(rows)
    def _pred(s, Mx, text, space):
        fs = [f for f in feats(text, 'char') if f in Mx.tot]; bh, bs = None, -1e18
        for h in space:
            sc = sum(math.log((Mx.cnt[f].get(h, 0) + .05) / (Mx.tot[f] + .05 * len(space))) for f in fs)
            if sc > bs: bh, bs = h, sc
        return bh
    def _lik(s, Mx, text, h, spacelen):
        fs = [f for f in feats(text, 'char') if f in Mx.tot]
        return sum(math.log((Mx.cnt[f].get(h, 0) + .05) / (Mx.tot[f] + .05 * spacelen)) for f in fs)
    def solve(s, text):
        t = text; best = None
        h1 = s._pred(s.A, t, HYP); r = run_hyp(h1, numbers_of(t))
        best = ((None, h1, None), math.log((s.bnd['__single__'][0] + 1) / (s.nsent + 2)) + s._lik(s.A, t, h1, len(HYP)))
        for k in range(1, len(t)):
            L_, R_ = t[:k], t[k:]
            h1 = s._pred(s.A, L_, HYP); h2 = s._pred(s.B, R_, H2)
            b = s.bnd[(t[k - 1], t[k])]; pb = (b[0] + 0.01) / (b[1] + 1.0)
            sc = math.log(pb) + s._lik(s.A, L_, h1, len(HYP)) + s._lik(s.B, R_, h2, len(H2))
            if sc > best[1]: best = ((k, h1, h2), sc)
        k, h1, h2 = best[0]
        if k is None: return run_hyp(h1, numbers_of(t)), best[0]
        return run2(h1, h2, t[:k], t[k:]), best[0]

def ev(model, rows, despace, solver='tok'):
    ok = 0; ok1 = 0; n1 = 0
    for _, t, a in rows:
        tt = t.replace(' ', '') if despace else t
        try: pred = model.solve(tt)[0]
        except Exception: pred = None
        ok += int(pred == a)
    return ok / len(rows)

rows = []
for sd in range(5):
    rng = random.Random(sd)
    train = [gen_th(rng) for _ in range(300)]
    m_tok = TwoStep(); m_tok.fit([(t, a) for _, t, a in train])
    m_ch = CharTwoStep(); m_ch.fit([(t.replace(' ', ''), a) for _, t, a in train])
    r = random.Random(500 + sd); test = [gen_th(r) for _ in range(200)]
    for name, mdl, ds in (('tok_spaced', m_tok, False), ('char_nospace', m_ch, True), ('ctl_tok_nospace', m_tok, True)):
        acc = ev(mdl, test, ds)
        row = {'seed': sd, 'arm': name, 'acc': round(acc, 3)}
        print(json.dumps(row), flush=True); rows.append(row)
print('DONE', flush=True)
