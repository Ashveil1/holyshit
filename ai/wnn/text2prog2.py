"""P16: (a) number WORDS (en+th) whose values are learned, (b) two-step sentences ("add 3 and 5 then multiply by 2").
(a) Stage A learns ops from digit sentences (as P15). Stage B sees sentences where number slots are sometimes words;
    for every token and value 1..10 it checks whether rewriting that token as the digit reproduces the answer under
    the stage-A learner; a token whose value works in >=80% of its sentences becomes a number word.
(b) The learner sees (sentence, answer) only. It explains each sentence by (split point, op1 on left clause, op2 on right
    clause applied to the first result) or by no split (single op); learns left-clause, right-clause and boundary-token weights.
GIVEN: skill library, hypothesis space, digit regex, whitespace tokens (Thai written with spaces), the candidate
    value range 1..10, the sentence templates. LEARNED: number-word values, op words, order, where clauses split.
python3 text2prog2.py"""
import re, sys, random, math
from collections import defaultdict
import text2prog as P
from text2prog import T, OPS, HYP, UNARY, run_hyp, numbers_of, feats, Learner, make, gen_set, evaluate
EN = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']
TH = ['หนึ่ง', 'สอง', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า', 'สิบ']
GOLD = {w: i + 1 for i, w in enumerate(EN)}; GOLD.update({w: i + 1 for i, w in enumerate(TH)})
def render(tmpl, vals, rng, pword):
    """fill a template; each value <=10 becomes a number word with prob pword (language follows the template)"""
    th = bool(re.search(r'[\u0e00-\u0e7f]', tmpl)); out = tmpl
    for k, v in vals.items():
        s = (TH if th else EN)[v - 1] if (1 <= v <= 10 and rng.random() < pword) else str(v)
        out = out.replace('{' + k + '}', s)
    return out
def ans_for(op, tmpl, a, b, c):
    if op in ('sub',): r = a - b
    elif op == 'div': r = a // b
    elif op == 'mod': r = a % b
    elif op == 'power': r = a ** b
    elif op in UNARY: r = OPS[op](a)
    elif op == 'gcd': r = math.gcd(a, b)
    else:
        nums = [x for k, x in (('a', a), ('b', b), ('c', c)) if '{' + k + '}' in tmpl]; r = OPS[op](*nums)
    return int(r)
def word_data(rng, which, n, big=False, pword=0.6, ops=None):
    out = []
    for _ in range(n):
        op = rng.choice(ops or list(T)); tm = rng.choice(T[op][which])
        a, b, c = P.draw(op, rng, big=False)
        a, b, c = (min(a, 10) if op not in ('power',) else a), b, c
        if op not in ('power', 'fact', 'sumto', 'isprime'):
            a, b, c = rng.randrange(1, 11), rng.randrange(1, 11), rng.randrange(1, 11)
            if op == 'sub' and a < b: a, b = b, a
            if op in ('div', 'mod'): b = rng.randrange(2, 11)
        if op == 'fact': a = rng.randrange(2, 9)
        if op == 'sumto': a = rng.randrange(3, 11)
        if op == 'isprime': a = rng.randrange(2, 11)
        text = render(tm, {'a': a, 'b': b, 'c': c}, rng, pword)
        out.append((op, text, ans_for(op, tm, a, b, c)))
    return out
def apply_lex(text, lex): return ' '.join(str(lex[w]) if w in lex else w for w in text.split())
def learn_lexicon(L, data, minv=3, rounds=4):
    lex = {}
    for _ in range(rounds):
        vote = defaultdict(lambda: defaultdict(int)); cnt = defaultdict(int)
        for _, text, ans in data:
            text = apply_lex(text, lex); toks = text.split()
            for w in set(toks):
                if re.search(r'\d', w): continue
                cnt[w] += 1
                for v in range(1, 11):
                    t2 = ' '.join(str(v) if x == w else x for x in toks)
                    try:
                        if L.answer(t2)[0] == ans: vote[w][v] += 1
                    except Exception: pass
        new = {}
        for w, c in cnt.items():
            vs = sorted(vote[w].items(), key=lambda t: -t[1])
            if not vs: continue
            top = vs[0][1]; second = vs[1][1] if len(vs) > 1 else 0
            if top >= minv and top >= 0.25 * c and top >= 2.5 * (second + 1) - 1: new[w] = vs[0][0]
        if not new: break
        lex.update(new)
    return lex
# ---------------- two-step sentences ----------------
H2 = [(o, d) for o in ('add', 'sub', 'mul', 'div', 'fact', 'isprime') for d in ('f', 'r') if not (o in ('fact', 'isprime') and d == 'r')]
C1 = {o: T[o] for o in ('add', 'sub', 'mul', 'gcd', 'max', 'min')}
C2 = {  # right clauses: (train, new frames)   {c} = the extra number
 'add': (["add {c}", "บวก {c}"], ["then also add {c} please", "และ ช่วย บวก {c}"]),
 'sub': (["subtract {c}", "ลบ {c}"], ["then also subtract {c} please", "และ ช่วย ลบ {c}"]),
 'mul': (["multiply by {c}", "คูณ ด้วย {c}"], ["then also multiply by {c} please", "และ ช่วย คูณ ด้วย {c}"]),
 'div': (["divide by {c}", "หาร ด้วย {c}"], ["then also divide by {c} please", "และ ช่วย หาร ด้วย {c}"]),
 'fact': (["take the factorial", "หา แฟกทอเรียล"], ["then also take the factorial please", "และ ช่วย หา แฟกทอเรียล"]),
 'isprime': (["check if it is prime", "ดู ว่า เป็น จำนวนเฉพาะ ไหม"], ["then also check if it is prime please", "และ ช่วย ดู ว่า เป็น จำนวนเฉพาะ ไหม"])}
CONN = (["then", "and then", "แล้ว", "จากนั้น"], ["after that", "afterwards", "ต่อ จาก นั้น", "หลัง จาก นั้น"])
def two_step(rng, which, big, p_single=0.3):
    if rng.random() < p_single:
        op = rng.choice(list(C1)); tm = rng.choice(C1[op][which]); t, a = make(op, tm, rng, big=False); return (op, None), t, a, None
    o1 = rng.choice(list(C1)); o2 = rng.choice(list(C2))
    t1, r1 = make(o1, rng.choice(C1[o1][0 if which == 0 else which]), rng, big=False)
    if o2 in ('fact',):
        for _ in range(50):
            if r1 <= 8: break
            t1, r1 = make(o1, rng.choice(C1[o1][0 if which == 0 else which]), rng, big=False)
        if r1 > 8: return two_step(rng, which, big)
    c = rng.randrange(2, 12)
    tm2 = rng.choice(C2[o2][0 if which == 0 else 1]); t2 = tm2.format(c=c)
    conn = rng.choice(CONN[0 if which == 0 else 1])
    if which == 1 and tm2.startswith('then also') or tm2.startswith('และ'): conn = ''
    if o2 == 'add': r = r1 + c
    elif o2 == 'sub': r = r1 - c
    elif o2 == 'mul': r = r1 * c
    elif o2 == 'div': r = r1 // c
    elif o2 == 'fact': r = math.factorial(r1)
    else: r = P.isp(r1)
    text = (t1 + ' ' + conn + ' ' + t2).replace('  ', ' ').strip()
    return (o1, o2), text, int(r), (len(t1.split()), conn)
def run2(h1, h2, left, right, prev=None):
    r1 = run_hyp(h1, numbers_of(left))
    if r1 is None: return None
    if h2 is None: return r1
    op, d = h2; nr = numbers_of(right)
    try:
        if op in ('fact', 'isprime'): return int(OPS[op](r1))
        if len(nr) != 1: return None
        a, b = (r1, nr[0]) if d == 'f' else (nr[0], r1)
        return int(OPS[op](a, b))
    except Exception: return None
def splits(toks):
    return [k for k in range(1, len(toks)) if any(re.search(r'\d', t) for t in toks[:k])]
class TwoStep:
    def __init__(s): s.A = Learner('tok'); s.B = Learner('tok'); s.bnd = defaultdict(lambda: [0.0, 0.0])   # B = right-clause learner over H2
    def fit(s, rows):
        HY2 = H2
        for text, ans in rows:
            toks = text.split(); E = []
            for h1 in HYP:
                r = run_hyp(h1, numbers_of(text))
                if r == ans: E.append((None, h1, None))
            for k in splits(toks):
                L_, R_ = ' '.join(toks[:k]), ' '.join(toks[k:])
                for h1 in HYP:
                    for h2 in HY2:
                        if run2(h1, h2, L_, R_) == ans: E.append((k, h1, h2))
            if any(k is None for k, _, _ in E): E = [e for e in E if e[0] is None]   # Occam: prefer the one-op reading
            if not E: continue
            w = 1.0 / len(E)
            for k, h1, h2 in E:
                if k is None:
                    for f in feats(text, 'tok'): s.A.tot[f] += w; s.A.cnt[f][h1] += w
                else:
                    L_, R_ = ' '.join(toks[:k]), ' '.join(toks[k:])
                    for f in feats(L_, 'tok'): s.A.tot[f] += w; s.A.cnt[f][h1] += w
                    for f in feats(R_, 'tok'): s.B.tot[f] += w; s.B.cnt[f][h2] += w
            # boundary statistics: token pair at the cut (positive credit) vs every candidate cut
            for k in splits(toks):
                f = (toks[k - 1], toks[k]); s.bnd[f][1] += 1
            for k, h1, h2 in E:
                if k is not None: s.bnd[(toks[k - 1], toks[k])][0] += w
            for k in (None,):
                pass
            s.bnd['__single__'][0] += sum(w for k, _, _ in E if k is None)
        s.nsent = getattr(s, 'nsent', 0) + len(rows)
    def solve(s, text):
        toks = text.split(); best = (None, -1e18)
        # single-op reading
        h, n = s.A.predict(text); r = run_hyp(h, numbers_of(text))
        single_score = math.log((s.bnd['__single__'][0] + 1) / (s.nsent + 2)) + s._lik(s.A, text, h)
        best = ((None, h, None), single_score)
        for k in splits(toks):
            L_, R_ = ' '.join(toks[:k]), ' '.join(toks[k:])
            h1, _ = s.A.predict(L_); h2 = s._pred(s.B, R_, H2)
            b = s.bnd[(toks[k - 1], toks[k])]; pb = (b[0] + 0.01) / (b[1] + 1.0)
            sc = math.log(pb) + s._lik(s.A, L_, h1) + s._lik2(s.B, R_, h2)
            if sc > best[1]: best = ((k, h1, h2), sc)
        k, h1, h2 = best[0]
        if k is None: return run_hyp(h1, numbers_of(text)), best[0]
        return run2(h1, h2, ' '.join(toks[:k]), ' '.join(toks[k:])), best[0]
    def _pred(s, M, text, space):
        fs = [f for f in feats(text, 'tok') if f in M.tot]; bh, bs = None, -1e18
        for h in space:
            sc = sum(math.log((M.cnt[f].get(h, 0) + .05) / (M.tot[f] + .05 * len(space))) for f in fs)
            if sc > bs: bh, bs = h, sc
        return bh
    def _lik(s, M, text, h):
        fs = [f for f in feats(text, 'tok') if f in M.tot]
        return sum(math.log((M.cnt[f].get(h, 0) + .05) / (M.tot[f] + .05 * len(HYP))) for f in fs)
    def _lik2(s, M, text, h):
        fs = [f for f in feats(text, 'tok') if f in M.tot]
        return sum(math.log((M.cnt[f].get(h, 0) + .05) / (M.tot[f] + .05 * len(H2))) for f in fs)
def main():
    seeds = range(5)
    print('== (a) number words: learned lexicon ==', flush=True)
    for nB in (150, 400, 1000):
        accs, lexacc, spur = [], [], []
        for sd in seeds:
            rng = random.Random(sd)
            L = Learner('tok'); L.fit([(t, a) for _, t, a in gen_set(rng, 0, 300)])
            lex = learn_lexicon(L, word_data(rng, 0, nB))
            good = sum(1 for w, v in GOLD.items() if lex.get(w) == v); lexacc.append(good / len(GOLD)); spur.append(len([w for w in lex if w not in GOLD]))
            r = random.Random(100 + sd); rows = word_data(r, 1, 300, pword=0.7)
            ok = 0
            for _, t, a in rows:
                try: ok += L.answer(apply_lex(t, lex))[0] == a
                except Exception: pass
            accs.append(ok / len(rows))
        g = []
        for sd in seeds:
            rng = random.Random(sd); L = Learner('tok'); L.fit([(t, a) for _, t, a in gen_set(rng, 0, 300)])
            r = random.Random(100 + sd); rows = word_data(r, 1, 300, pword=0.7); ok = 0
            for _, t, a in rows:
                try: ok += L.answer(apply_lex(t, GOLD))[0] == a
                except Exception: pass
            g.append(ok / len(rows))
        n0 = []
        for sd in seeds:
            rng = random.Random(sd); L = Learner('tok'); L.fit([(t, a) for _, t, a in gen_set(rng, 0, 300)])
            r = random.Random(100 + sd); rows = word_data(r, 1, 300, pword=0.7); ok = 0
            for _, t, a in rows:
                try: ok += L.answer(t)[0] == a
                except Exception: pass
            n0.append(ok / len(rows))
        print(f'word-sentences n={nB:3d}: words learned {sum(lexacc)/5*20:.1f}/20 (spurious entries {sum(spur)/5:.1f}); answer acc on unseen frames with words: learned-lexicon {sum(accs)/5:.2f} | gold lexicon {sum(g)/5:.2f} | no lexicon {sum(n0)/5:.2f}', flush=True)
    print('== (b) two-step sentences ==', flush=True)
    for n in (100, 300, 1000):
        res = defaultdict(list)
        for sd in seeds:
            rng = random.Random(sd); M = TwoStep(); M.fit([(t, a) for _, t, a, _ in (two_step(rng, 0, False) for _ in range(n))])
            r = random.Random(100 + sd)
            for nm, wh in (('same phrasing', 0), ('new connectors+frames', 1)):
                ok = sp = tot = 0
                for _ in range(300):
                    kind, t, a, info = two_step(r, wh, True)
                    try: pred, cfg = M.solve(t)
                    except Exception: pred, cfg = None, (None, None, None)
                    ok += pred == a; tot += 1
                    if info is not None: sp += (cfg[0] is not None and cfg[0] == info[0])
                res[nm].append(ok / tot)
        print(f'two-step n={n:4d}: ' + ' | '.join(f'{k} {sum(v)/5:.2f} [{min(v):.2f}-{max(v):.2f}]' for k, v in res.items()), flush=True)
if __name__ == "__main__": main()
