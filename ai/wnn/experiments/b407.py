import random, json, math
from collections import defaultdict
import text2prog2
from text2prog2 import TwoStep, splits, run_hyp, numbers_of, feats, HYP, H2, two_step, C1, C2, CONN, make

NEWOPS = {'double': lambda r: r * 2, 'triple': lambda r: r * 3, 'halve': lambda r: r // 2,
          'inc': lambda r: r + 1, 'dec': lambda r: r - 1}
ANAPH = [('double', 'then double it'), ('triple', 'then triple it'), ('halve', 'then halve it'),
         ('inc', 'then increment it'), ('dec', 'then decrement it')]

_orig_run2 = text2prog2.run2
def run2x(h1, h2, left, right, prev=None):
    if h2 is not None and h2[0] in NEWOPS:
        r1 = run_hyp(h1, numbers_of(left))
        if r1 is None: return None
        if len(numbers_of(right)) != 0: return None  # anaphoric clause must carry no digits
        return NEWOPS[h2[0]](r1)
    return _orig_run2(h1, h2, left, right, prev)
text2prog2.run2 = run2x
for o in NEWOPS: text2prog2.H2.append((o, 'f'))

import text2prog2 as M

def gen_anaph(rng, which=0, p_anaph=0.35, p_single=0.3):
    # mirror two_step; with prob p_anaph the 2-step right clause is anaphoric
    if rng.random() < p_single:
        op = rng.choice(list(C1)); tm = rng.choice(C1[op][which]); t, a = make(op, tm, rng, big=False)
        return ('single',), t, a
    o1 = rng.choice(list(C1))
    t1, r1 = make(o1, rng.choice(C1[o1][0]), rng, big=False)
    if rng.random() < p_anaph:
        o2, phrase = ANAPH[rng.randrange(len(ANAPH))]
        r = NEWOPS[o2](r1)
        return (o1, o2), (t1 + ' ' + phrase).strip(), int(r)
    o2 = rng.choice(list(C2))
    if o2 in ('fact',):
        for _ in range(50):
            if r1 <= 8: break
            t1, r1 = make(o1, rng.choice(C1[o1][0]), rng, big=False)
        if r1 > 8: return gen_anaph(rng, which, p_anaph)
    c = rng.randrange(2, 12)
    tm2 = rng.choice(C2[o2][0]); t2 = tm2.format(c=c)
    conn = rng.choice(CONN[0])
    if o2 == 'add': r = r1 + c
    elif o2 == 'sub': r = r1 - c
    elif o2 == 'mul': r = r1 * c
    elif o2 == 'div': r = r1 // c
    elif o2 == 'fact': r = math.factorial(r1)
    else: r = M.P.isp(r1)
    return (o1, o2), (t1 + ' ' + conn + ' ' + t2).replace('  ', ' ').strip(), int(r)

def gen_explicit(rng):
    # same but never anaphoric
    return gen_anaph(rng, 0, 0.0)

def eval_model(model, rng, n, anaph_only):
    ok = 0
    for _ in range(n):
        _, t, a = gen_anaph(rng, 0, 1.0, 0.0) if anaph_only else gen_anaph(rng, 0, 0.0, 0.0)
        try: ok += int(model.solve(t)[0] == a)
        except Exception: pass
    return ok / n

rows = []
for sd in range(5):
    rng = random.Random(sd)
    train_mix = [gen_anaph(rng, 0, 0.35) for _ in range(300)]
    m_mix = TwoStep(); m_mix.fit([(t, a) for _, t, a in train_mix])
    rng2 = random.Random(sd)  # control: same stream position, 0% anaphora
    train_ctl = [gen_explicit(rng2) for _ in range(300)]
    m_ctl = TwoStep(); m_ctl.fit([(t, a) for _, t, a in train_ctl])
    for name, mdl, aonly in (('mix_anaph', m_mix, True), ('mix_expl', m_mix, False),
                             ('ctl_anaph', m_ctl, True), ('ctl_expl', m_ctl, False)):
        r = random.Random(1000 + sd)
        acc = eval_model(mdl, r, 100, aonly)
        row = {'seed': sd, 'arm': name, 'acc': round(acc, 3)}
        print(json.dumps(row), flush=True); rows.append(row)
print('DONE', flush=True)
