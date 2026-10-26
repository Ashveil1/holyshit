"""B-503: learn number words JOINTLY with the 2-step model vs P16 separate stages.
SEPARATE (P16 baseline): TwoStep fit on digit sentences, frozen; learn_lexicon (P16 defaults)
against it; eval via apply_lex. JOINT: interleaved rounds - one lexicon voting round against
the current model, then refit the model on digit sentences + lexicon-decoded word sentences.
Same corpora, same thresholds, same eval. 5 seeds. Sizes fixed pre-run (LEDGER B-503)."""
import random, math, json, re, sys, time
from collections import defaultdict
import text2prog as P
from text2prog2 import TwoStep, two_step, learn_lexicon, apply_lex, GOLD, EN, TH

N_DIGIT = 600      # stage-A digit 2-step sentences (both arms)
N_WORD = 200       # word-substituted 2-step train sentences (both arms)
ROUNDS = 4         # lexicon voting rounds (P16 default)
PWORD_TRAIN = 0.6  # P16 render default
PWORD_EVAL = 0.7   # P16 eval default
N_EVAL = 300
SEEDS = range(5)

def wordsub(t, rng, pword):
    out = []
    for tok in t.split():
        if tok.isdigit() and 1 <= int(tok) <= 10 and rng.random() < pword:
            out.append((TH if rng.random() < 0.5 else EN)[int(tok) - 1])
        else:
            out.append(tok)
    return ' '.join(out)

def gen_digit(rng, n):
    return [(t, a) for _, t, a, _ in (two_step(rng, 0, False) for _ in range(n))]

def gen_word(rng, which, n, pword):
    rows = []
    for _ in range(n):
        _, t, a, _ = two_step(rng, which, False)
        rows.append((0, wordsub(t, rng, pword), a))
    return rows

class W:  # learn_lexicon expects .answer(t)[0]
    def __init__(s, M): s.M = M
    def answer(s, t):
        try: return (s.M.solve(t)[0],)
        except Exception: return (None,)

def lex_round(L, data, lex, minv=3):
    """one learn_lexicon round (same thresholds) starting from an existing lexicon"""
    vote = defaultdict(lambda: defaultdict(int)); cnt = defaultdict(int)
    for _, text, ans in data:
        text = apply_lex(text, lex); toks = text.split()
        for w in set(toks):
            if re.search(r'\d', w): continue
            cnt[w] += 1
            for v in range(1, 11):
                t2 = ' '.join(str(v) if x == w else x for x in toks)
                if L.answer(t2)[0] == ans: vote[w][v] += 1
    new = {}
    for w, c in cnt.items():
        vs = sorted(vote[w].items(), key=lambda t: -t[1])
        if not vs: continue
        top = vs[0][1]; second = vs[1][1] if len(vs) > 1 else 0
        if top >= minv and top >= 0.25 * c and top >= 2.5 * (second + 1) - 1: new[w] = vs[0][0]
    return new

def arm(sd):
    rng = random.Random(sd)
    digit = gen_digit(rng, N_DIGIT)
    word = gen_word(rng, 0, N_WORD, PWORD_TRAIN)
    # SEPARATE (P16): frozen stage-A model
    M0 = TwoStep(); M0.fit(digit)
    lex_s = learn_lexicon(W(M0), word, rounds=ROUNDS)
    # JOINT: interleaved voting + refit on digit + decoded word sentences
    lex_j = {}; MJ = TwoStep(); MJ.fit(digit)
    for _ in range(ROUNDS):
        new = lex_round(W(MJ), word, lex_j)
        if not new: break
        lex_j.update(new)
        MJ = TwoStep(); MJ.fit(digit + [(apply_lex(t, lex_j), a) for _, t, a in word])
    r = random.Random(100 + sd)
    test = gen_word(r, 1, N_EVAL, PWORD_EVAL)
    ok_s = ok_j = 0
    for _, t, a in test:
        try: ok_s += int(M0.solve(apply_lex(t, lex_s))[0] == a)
        except Exception: pass
        try: ok_j += int(MJ.solve(apply_lex(t, lex_j))[0] == a)
        except Exception: pass
    stats = lambda lex: (sum(1 for w, v in GOLD.items() if lex.get(w) == v),
                         len([w for w in lex if w not in GOLD]),
                         sum(1 for w, v in GOLD.items() if w in lex and lex[w] != v))
    gs, ss, ws = stats(lex_s); gj, sj, wj = stats(lex_j)
    row = {'seed': sd, 'acc_sep': round(ok_s / N_EVAL, 3), 'acc_joint': round(ok_j / N_EVAL, 3),
           'gold_sep': gs, 'spur_sep': ss, 'wrongval_sep': ws,
           'gold_joint': gj, 'spur_joint': sj, 'wrongval_joint': wj}
    print(json.dumps(row), flush=True)
    return row

if __name__ == '__main__':
    t0 = time.time()
    rows = [arm(sd) for sd in SEEDS]
    m = lambda k: round(sum(r[k] for r in rows) / len(rows), 3)
    summ = {'acc_sep': m('acc_sep'), 'acc_joint': m('acc_joint'),
            'gold_sep': m('gold_sep'), 'gold_joint': m('gold_joint'),
            'spur_sep': m('spur_sep'), 'spur_joint': m('spur_joint'),
            'wrongval_sep': m('wrongval_sep'), 'wrongval_joint': m('wrongval_joint'),
            'n_digit': N_DIGIT, 'n_word': N_WORD, 'rounds': ROUNDS, 'seeds': len(rows),
            'wall_s': round(time.time() - t0)}
    print('SUMMARY ' + json.dumps(summ), flush=True)
    print('DONE', flush=True)
