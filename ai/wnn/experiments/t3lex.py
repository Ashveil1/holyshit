"""P16 word-lexicon hyperparameter grid (B-129..152+): learn_lexicon with (minv, mass, margin, rounds).
Backlog mapping: 'minmass 1.5' -> minv=1.5 (>=2 votes; default 3), 'margin' -> the 2.5x runner-up factor, 'rounds' -> rounds.
Baseline = P16 defaults (minv=3, mass .25, margin 2.5, rounds 4). Success: more gold words at same n, spurious <= +1."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import random, re
from collections import defaultdict
import text2prog2 as T2
from text2prog2 import Learner, gen_set, word_data, apply_lex, GOLD
def learn_lex(L, data, minv, mass, margin, rounds):
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
            if top >= minv and top >= mass * c and top >= margin * (second + 1) - 1: new[w] = vs[0][0]
        if not new: break
        lex.update(new)
    return lex
def cell(minv, margin, rounds, nB):
    lexacc, spur, accs = [], [], []
    for sd in range(5):
        rng = random.Random(sd)
        L = Learner('tok'); L.fit([(t, a) for _, t, a in gen_set(rng, 0, 300)])
        lex = learn_lex(L, word_data(rng, 0, nB), minv, 0.25, margin, rounds)
        lexacc.append(sum(1 for w, v in GOLD.items() if lex.get(w) == v)); spur.append(len([w for w in lex if w not in GOLD]))
        r = random.Random(100 + sd); rows = word_data(r, 1, 300, pword=0.7)
        ok = 0
        for _, t, a in rows:
            try: ok += L.answer(apply_lex(t, lex))[0] == a
            except Exception: pass
        accs.append(ok / len(rows))
    return sum(lexacc) / 5, sum(spur) / 5, sum(accs) / 5
if __name__ == '__main__':
    for nB in (60, 150, 400):
        g, s, a = cell(3, 2.5, 4, nB)
        print(f'DEFAULT n={nB:3d}: gold {g:.1f}/20 spur {s:.1f} acc {a:.2f}', flush=True)
    for minv, margin, rounds in [(1.5, 2, 2), (1.5, 2, 4), (1.5, 2.5, 2), (1.5, 2.5, 4), (1.5, 4, 2), (1.5, 4, 4)]:
        for nB in (60, 150, 400):
            g, s, a = cell(minv, margin, rounds, nB)
            print(f'minv={minv} margin={margin} rounds={rounds} n={nB:3d}: gold {g:.1f}/20 spur {s:.1f} acc {a:.2f}', flush=True)
