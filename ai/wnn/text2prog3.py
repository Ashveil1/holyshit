"""P17: fix the two weak spots of P16.
(a) number words from FEWER examples: a token is a candidate number word only if it occurs in a slot context
    (prev,next token, or prev only, or next only) where DIGITS occurred in the digit-sentence data (distributional
    alignment, learned, no list of number words); candidates are then voted on as in P16.
(b) two-step sentences with NEW connectors: the cut-point model uses token TYPES (digit / known word / unseen word)
    at the cut instead of the exact token pair, so an unseen connector ("after that") is still a plausible cut.
python3 text2prog3.py"""
import re, sys, random, math
from collections import defaultdict
import text2prog as P
import text2prog2 as Q
from text2prog import Learner, gen_set, numbers_of, feats, HYP
from text2prog2 import (word_data, apply_lex, GOLD, two_step, TwoStep, run2, splits, H2)
def is_digit(t): return bool(re.fullmatch(r'\d+', t))
def digit_contexts(texts):
    ctx = set()
    for t in texts:
        w = t.split()
        for i, x in enumerate(w):
            if is_digit(x):
                p = w[i - 1] if i else '^'; n = w[i + 1] if i + 1 < len(w) else '$'
                ctx.add(('pn', p, n)); ctx.add(('p', p)); ctx.add(('n', n))
    return ctx
def candidate(w_i, w, ctx):
    p = w[w_i - 1] if w_i else '^'; n = w[w_i + 1] if w_i + 1 < len(w) else '$'
    return ('pn', p, n) in ctx or (('p', p) in ctx and ('n', n) in ctx) or ('p', p) in ctx or ('n', n) in ctx
def learn_lexicon2(L, data, ctx, minv=2, rounds=4, use_ctx=True):
    lex = {}
    for _ in range(rounds):
        vote = defaultdict(lambda: defaultdict(int)); cnt = defaultdict(int)
        for _, text, ans in data:
            text = apply_lex(text, lex); toks = text.split()
            seen = set()
            for i, w in enumerate(toks):
                if is_digit(w) or w in seen: continue
                if use_ctx and not candidate(i, toks, ctx): continue
                seen.add(w); cnt[w] += 1
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
class TwoStep2(TwoStep):
    """boundary model over token TYPES at the cut"""
    def typ(s, t): return 'D' if is_digit(t) else ('K' if (t in s.A.known or t in s.B.known) else 'U')
    def fit(s, rows):
        TwoStep.fit(s, rows)
        s.A.known = {f for f in s.A.tot if isinstance(f, str)}; s.B.known = {f for f in s.B.tot if isinstance(f, str)}
        s.tb = defaultdict(lambda: [0.0, 0.0])
        for text, ans in rows:
            toks = text.split(); E = []
            for k in splits(toks):
                L_, R_ = ' '.join(toks[:k]), ' '.join(toks[k:])
                for h1 in HYP:
                    for h2 in H2:
                        if run2(h1, h2, L_, R_) == ans: E.append(k)
            single = any(P.run_hyp(h, numbers_of(text)) == ans for h in HYP)
            if single or not E: 
                for k in splits(toks): s.tb[(s.typ(toks[k - 1]), s.typ(toks[k]))][1] += 1
                continue
            w = 1.0 / len(E)
            for k in splits(toks): s.tb[(s.typ(toks[k - 1]), s.typ(toks[k]))][1] += 1
            for k in E: s.tb[(s.typ(toks[k - 1]), s.typ(toks[k]))][0] += w
    def solve(s, text):
        toks = text.split()
        h, n = s.A.predict(text)
        best = ((None, h, None), math.log((s.bnd['__single__'][0] + 1) / (s.nsent + 2)) + s._lik(s.A, text, h))
        for k in splits(toks):
            L_, R_ = ' '.join(toks[:k]), ' '.join(toks[k:])
            h1, _ = s.A.predict(L_); h2 = s._pred(s.B, R_, H2)
            b = s.tb[(s.typ(toks[k - 1]), s.typ(toks[k]))]; pb = (b[0] + 0.01) / (b[1] + 1.0)
            sc = math.log(pb) + s._lik(s.A, L_, h1) + s._lik2(s.B, R_, h2)
            if sc > best[1]: best = ((k, h1, h2), sc)
        k, h1, h2 = best[0]
        if k is None: return P.run_hyp(h1, numbers_of(text)), best[0]
        return run2(h1, h2, ' '.join(toks[:k]), ' '.join(toks[k:])), best[0]
def main():
    seeds = range(5)
    print('== (a) number words, fewer examples (candidates restricted to digit-like slot contexts) ==', flush=True)
    for nB in (30, 60, 150, 400):
        out = {}
        for use_ctx in (False, True):
            accs, lw, sp = [], [], []
            for sd in seeds:
                rng = random.Random(sd); dig = gen_set(rng, 0, 300)
                L = Learner('tok'); L.fit([(t, a) for _, t, a in dig]); ctx = digit_contexts([t for _, t, a in dig])
                lex = learn_lexicon2(L, word_data(rng, 0, nB), ctx, use_ctx=use_ctx)
                lw.append(sum(1 for w, v in GOLD.items() if lex.get(w) == v)); sp.append(len([w for w in lex if w not in GOLD]))
                r = random.Random(100 + sd); rows = word_data(r, 1, 300, pword=0.7); ok = 0
                for _, t, a in rows:
                    try: ok += L.answer(apply_lex(t, lex))[0] == a
                    except Exception: pass
                accs.append(ok / len(rows))
            out[use_ctx] = (sum(lw) / 5, sum(sp) / 5, sum(accs) / 5)
        print(f'n={nB:4d}: P16 method words {out[False][0]:.1f}/20 spur {out[False][1]:.1f} acc {out[False][2]:.2f} | with slot-context candidates words {out[True][0]:.1f}/20 spur {out[True][1]:.1f} acc {out[True][2]:.2f}', flush=True)
    print('== (b) two-step sentences, type-based cut model ==', flush=True)
    for n in (100, 300, 1000):
        res = defaultdict(list)
        for sd in seeds:
            rng = random.Random(sd); rows = [(t, a) for _, t, a, _ in (two_step(rng, 0, False) for _ in range(n))]
            for nm, cls in (('P16', TwoStep), ('types', TwoStep2)):
                M = cls(); M.fit(rows); r = random.Random(100 + sd)
                for wh, wn in ((0, 'same'), (1, 'new')):
                    ok = 0
                    for _ in range(300):
                        kind, t, a, info = two_step(r, wh, True)
                        try: ok += M.solve(t)[0] == a
                        except Exception: pass
                    res[(nm, wn)].append(ok / 300)
        print(f'n={n:4d}: ' + ' | '.join(f'{k[0]} {k[1]} {sum(v)/5:.2f} [{min(v):.2f}-{max(v):.2f}]' for k, v in res.items()), flush=True)
if __name__ == '__main__' and len(sys.argv) == 1: main()

import itertools
def learn_lexicon3(L, data, ctx, minmass=2.0, margin=2.5, rounds=2):
    """joint explanation: all candidate tokens of a sentence get values together; credit is shared among consistent assignments"""
    lex = {}
    for _ in range(rounds):
        mass = defaultdict(lambda: defaultdict(float)); cnt = defaultdict(int)
        for _, text, ans in data:
            toks = apply_lex(text, lex).split(); cands = []
            for i, w in enumerate(toks):
                if not is_digit(w) and w not in cands and candidate(i, toks, ctx): cands.append(w)
            if not cands or len(cands) > 3: continue
            for w in cands: cnt[w] += 1
            good = []
            for vals in itertools.product(range(1, 11), repeat=len(cands)):
                m = dict(zip(cands, vals)); t2 = ' '.join(str(m[x]) if x in m else x for x in toks)
                try:
                    if L.answer(t2)[0] == ans: good.append(m)
                except Exception: pass
            if good:
                for m in good:
                    for w, v in m.items(): mass[w][v] += 1.0 / len(good)
        new = {}
        for w, c in cnt.items():
            vs = sorted(mass[w].items(), key=lambda t: -t[1])
            if not vs: continue
            top = vs[0][1]; second = vs[1][1] if len(vs) > 1 else 0.0
            if top >= minmass and top >= 0.2 * c and top >= margin * (second + 0.5): new[w] = vs[0][0]
        if not new: break
        lex.update(new)
    return lex
def main3():
    print('== (a2) joint explanation of number words ==', flush=True)
    for nB in (30, 60, 150, 400):
        lw, sp, accs = [], [], []
        for sd in range(5):
            rng = random.Random(sd); dig = gen_set(rng, 0, 300)
            L = Learner('tok'); L.fit([(t, a) for _, t, a in dig]); ctx = digit_contexts([t for _, t, a in dig])
            lex = learn_lexicon3(L, word_data(rng, 0, nB), ctx)
            lw.append(sum(1 for w, v in GOLD.items() if lex.get(w) == v)); sp.append(len([w for w in lex if w not in GOLD]))
            r = random.Random(100 + sd); rows = word_data(r, 1, 300, pword=0.7); ok = 0
            for _, t, a in rows:
                try: ok += L.answer(apply_lex(t, lex))[0] == a
                except Exception: pass
            accs.append(ok / len(rows))
        print(f'n={nB:4d}: joint method words {sum(lw)/5:.1f}/20 spur {sum(sp)/5:.1f} acc {sum(accs)/5:.2f}', flush=True)
if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'a2': main3()
