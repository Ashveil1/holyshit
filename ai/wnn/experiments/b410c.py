import random, json, math
from collections import defaultdict
import text2prog as P
from text2prog2 import TwoStep, learn_lexicon, apply_lex, Learner
from b410 import EN, UNARY, TPL, pin
import random as _r
def unary_sent(rng, vocab_range=(1, 11), wrong_ans=False):
    op = rng.choice(list(UNARY)); v = rng.randrange(*vocab_range)
    wd = EN[v - 1]; a = UNARY[op](v)
    if wrong_ans: a = a + rng.randrange(1, 5)
    return wd, TPL[op].format(w=wd), a

BIN = {'add': (["add {a} and {b}", "what is {a} plus {b}"], lambda a, b: a + b),
       'sub': (["{a} minus {b}", "subtract {b} from {a}"], lambda a, b: a - b),
       'mul': (["multiply {a} by {b}", "{a} times {b}"], lambda a, b: a * b),
       'gcd': (["gcd of {a} and {b}", "gcd {a} {b}"], lambda a, b: math.gcd(a, b))}
STEP2 = {'add': ("then add {c}", lambda r, c: r + c), 'sub': ("then subtract {c}", lambda r, c: r - c),
         'mul': ("then multiply by {c}", lambda r, c: r * c), 'div': ("then divide by {c}", lambda r, c: r // c)}

def w(v): return EN[v - 1]

def gen_bin(rng, words):
    op = rng.choice(list(BIN)); tmpls, f = BIN[op]
    a, b = rng.randrange(1, 11), rng.randrange(1, 11)
    if op == 'sub' and a < b: a, b = b, a
    tm = rng.choice(tmpls)
    fmt = (lambda v: w(v)) if words else str
    return tm.format(a=fmt(a), b=fmt(b)), f(a, b)

def gen_2step(rng, words):
    op = rng.choice(list(BIN)); tmpls, f = BIN[op]
    a, b = rng.randrange(1, 11), rng.randrange(1, 11)
    if op == 'sub' and a < b: a, b = b, a
    r1 = f(a, b)
    o2 = rng.choice(list(STEP2)); tm2, f2 = STEP2[o2]
    c = rng.randrange(2, 11)
    fmt = (lambda v: w(v)) if words else str
    t = rng.choice(tmpls).format(a=fmt(a), b=fmt(b)) + ' ' + tm2.format(c=fmt(c))
    return t, f2(r1, c)

def gen_mix(rng, words, p2=0.5):
    return gen_2step(rng, words) if rng.random() < p2 else gen_bin(rng, words)

NWORDS = re_words = set(EN)
def decodable(t, lex): return all(x in lex or not re_words.__contains__(x) for x in t.split())

rows = []
for sd in range(5):
    rng = random.Random(sd)
    unary = [unary_sent(rng) for _ in range(120)]
    mixed_w = [gen_mix(rng, True) for _ in range(600)]
    mixed_d = [gen_mix(rng, False) for _ in range(600)]
    # digit-free arm
    cand = pin(unary)
    lex0 = {wd: next(iter(c)) for wd, c in cand.items() if len(c) == 1}
    dec = [(apply_lex(t, lex0), a) for t, a in mixed_w if decodable(t, lex0)]
    m_bin = Learner('tok'); m_bin.fit(dec)
    lex2 = learn_lexicon(m_bin, [('?', t, a) for t, a in mixed_w])
    lex = dict(lex0); lex.update(lex2)
    # EM round 2: retrain on fully decoded corpus with the complete lexicon, re-vote
    dec2 = [(apply_lex(t, lex), a) for t, a in mixed_w if decodable(t, lex)]
    m_bin2 = Learner('tok'); m_bin2.fit(dec2)
    lex3 = learn_lexicon(m_bin2, [('?', t, a) for t, a in mixed_w])
    lex.update(lex3)
    m2 = TwoStep(); m2.fit([(apply_lex(t, lex), a) for t, a in mixed_w])
    # baseline: digit model
    mb = TwoStep(); mb.fit(mixed_d)
    r = random.Random(700 + sd)
    test_w = [gen_mix(r, True) for _ in range(200)]
    r2 = random.Random(700 + sd)
    test_d = [gen_mix(r2, False) for _ in range(200)]
    ok = okb = 0
    for (t, a), (td, ad) in zip(test_w, test_d):
        try: ok += int(m2.solve(apply_lex(t, lex))[0] == a)
        except Exception: pass
        try: okb += int(mb.solve(td)[0] == ad)
        except Exception: pass
    rows.append({'seed': sd, 'lex0': len(lex0), 'lex_total': len(lex),
                 'lex_correct': sum(1 for wd, v in lex.items() if EN[v - 1] == wd),
                 'decoded': len(dec), 'acc': round(ok / 200, 3), 'base': round(okb / 200, 3)})
    print(json.dumps(rows[-1]), flush=True)
print('DONE', flush=True)
