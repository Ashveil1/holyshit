import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import random, json, re
from collections import defaultdict
import text2prog as P
import text2prog2
from text2prog2 import TwoStep, learn_lexicon, apply_lex, numbers_of, C1, C2, CONN, make, run2, run_hyp

EN = ['one','two','three','four','five','six','seven','eight','nine','ten']
UNARY = {'fact': lambda v: __import__('math').factorial(v),
         'sumto': lambda v: v * (v + 1) // 2,
         'isprime': lambda v: int(P.isp(v))}
TPL = {'fact': 'factorial of {w}', 'sumto': 'sum from one to {w}', 'isprime': 'check whether {w} is prime'}

def unary_sent(rng, vocab_range=(2, 10), wrong_ans=False):
    op = rng.choice(list(UNARY)); v = rng.randrange(*vocab_range)
    w = EN[v - 1]; a = UNARY[op](v)
    if wrong_ans: a = a + rng.randrange(1, 5)
    return w, TPL[op].format(w=w), a

def pin(sents):
    cand = defaultdict(set)
    for w, t, a in sents:
        pre = {v for v in range(1, 11) for f in UNARY.values() if f(v) == a}
        cand[w] = cand[w] & pre if w in cand else set(pre)
    return cand

def phase1(n, sd, wrong=False):
    rng = random.Random(sd)
    sents = [unary_sent(rng, wrong_ans=wrong) for _ in range(n)]
    cand = pin(sents)
    gold = {EN[v - 1]: v for v in range(2, 11)}
    pinned = {w: next(iter(c)) for w, c in cand.items() if len(c) == 1}
    correct = sum(1 for w, v in pinned.items() if gold.get(w) == v)
    return {'n': n, 'seed': sd, 'wrong': wrong, 'seen': len(cand),
            'pinned': len(pinned), 'correct': correct}

rows = []
for n in (150, 400):
    for sd in range(5):
        rows.append(phase1(n, sd)); rows.append(phase1(n, sd + 1000, wrong=True))
for r in rows: print(json.dumps(r), flush=True)
print('DONE', flush=True)
