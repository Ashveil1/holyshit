#!/usr/bin/env python3
"""P6 reference model + experiments: a working-memory procedure machine that
learns arithmetic PROCEDURES from demonstration traces (ACT-R style: a
learned production policy over a working memory, plus declarative fact memory).

GIVEN (hand-built, not learned):  the primitive actions READ/FACT/WRITE/ADV/HALT,
  the tape layout (digits LSB-first), the abstraction of the carry register to
  'zero / nonzero' for the policy, the successor demos 0..9, the sentence
  template + number extraction for word problems, the teacher that emits traces.
LEARNED:  (1) policy: observation -> next action, from traces (majority vote);
  (2) declarative memory: (op,x,y,c) -> (out,c') facts, from FACT steps in traces;
  (3) successor memory (from 0..9 counting demos) and (4) verb->operation map.
Deterministic: same xr_next RNG as the .holy files. Run: python3 reason.py [T1..T5]
"""
import sys, itertools
import numpy as np

MASK = 17592186044415
def xr_next(s):
    s = (s ^ ((s << 13) & MASK)) & MASK
    s = s ^ (s >> 7)
    s = (s ^ ((s << 17) & MASK)) & MASK
    return s

class Rng:
    def __init__(self, seed): self.s = seed
    def next(self, n):
        self.s = xr_next(self.s + 1); return self.s % n

READ, FACT, WRITE, ADV, HALT, START = 0, 1, 2, 3, 4, 5
ADD, SUB, MUL, CMP = 0, 1, 2, 3
OPN = ['add', 'sub', 'mul', 'cmp']

def digits(n):
    d = []
    while True:
        d.append(n % 10); n //= 10
        if n == 0: return d
def undigits(d): return sum(v * 10 ** i for i, v in enumerate(d))

# ---- ground truth one-step functions (used ONLY by teacher + scoring) ----
def true_fact(op, x, y, c):
    if op == ADD:
        t = x + y + c; return t % 10, t // 10
    if op == SUB:
        t = x - y - c
        return (t + 10, 1) if t < 0 else (t, 0)
    if op == MUL:
        t = x * y + c; return t % 10, t // 10
    if op == CMP:                      # c: 0 equal so far, 1 a>b, 2 a<b ; no output digit
        return None, (1 if x > y else 2 if x < y else c)

def pair_is_test(a, b):
    return (a * 31 + b * 17) % 4 == 0        # deterministic held-out operand pairs

def sample_pair(rng, nd_a, nd_b, want_test):
    while True:
        def num(nd):
            if nd == 1: return rng.next(10)
            return 10 ** (nd - 1) + rng.next(9 * 10 ** (nd - 1))
        a, b = num(nd_a), num(nd_b)
        if nd_a > 3 or nd_b > 3 or pair_is_test(a, b) == want_test: return a, b

# ---- teacher: emits a demonstration trace (obs, action) + fact observations ----
def teacher_trace(op, A, B):
    """A,B digit lists LSB first (MUL: B is [k]). returns (steps, facts)."""
    steps, facts = [], []
    c = 0; i = 0; last = START; has_out = 0; a_bl = b_bl = 0
    def obs(): return (op, last, a_bl, b_bl, int(c != 0), has_out)
    while True:
        steps.append((obs(), READ)); last = READ
        a_bl = int(i >= len(A)); b_bl = 0 if op == MUL else int(i >= len(B))
        x = 0 if a_bl else A[i]
        y = B[0] if op == MUL else (0 if b_bl else B[i])
        done = a_bl and (b_bl or op == MUL) and (c == 0 or op == CMP)
        if done:
            steps.append((obs(), HALT)); return steps, facts, c
        steps.append((obs(), FACT)); last = FACT
        out, c2 = true_fact(op, x, y, c)
        facts.append(((op, x, y, c), (out, c2)))
        c = c2; has_out = int(out is not None)
        steps.append((obs(), WRITE if has_out else ADV)); last = WRITE if has_out else ADV
        if has_out:
            steps.append((obs(), ADV)); last = ADV
        i += 1; has_out = 0

class Learner:
    def __init__(self):
        self.pol = {}       # obs -> {action: count}
        self.facts = {}     # (op,x,y,c) -> (out,c')
        self.succ = {}      # x -> (x+1)%10 , carry   (from counting demos)
    def watch(self, op, A, B):
        steps, facts, _ = teacher_trace(op, A, B)
        for o, a in steps:
            d = self.pol.setdefault(o, {}); d[a] = d.get(a, 0) + 1
        for k, v in facts: self.facts[k] = v
    def watch_counting(self):
        for x in range(10): self.succ[x] = ((x + 1) % 10, int(x == 9))
    def policy(self, o):
        d = self.pol.get(o)
        return None if d is None else max(d.items(), key=lambda kv: (kv[1], -kv[0]))[0]
    def fact(self, op, x, y, c, derive):
        k = (op, x, y, c)
        if k in self.facts: return self.facts[k]
        if not derive or op not in (ADD, SUB, MUL) or not self.succ: return None
        if op == MUL:               # GIVEN procedure: multiply = repeated addition, using learned ADD facts
            lo, hi = c % 10, c // 10
            for _ in range(y):
                r1 = self.fact(ADD, lo, x, 0, True)
                if r1 is None: return None
                lo, cr = r1
                r2 = self.fact(ADD, hi, 0, cr, True)
                if r2 is None: return None
                hi = r2[0]
            return lo, hi
        n = y + c; v = x; wrapped = 0
        if op == ADD:
            for _ in range(n):
                v, w = self.succ[v]; wrapped |= w
        else:                      # predecessor = inverse of learned successor
            pred = {s: (x0, w) for x0, (s, w) in self.succ.items()}
            for _ in range(n):
                v, w = pred[v]; wrapped |= w
        return v, wrapped

def run(L, op, A, B, derive=True, flip_carry_at=None, drop_carry=False, step_cap=100000):
    """execute the learned machine. returns (out digits, final c) or None on failure."""
    out = []; c = 0; i = 0; last = START; has_out = 0; a_bl = b_bl = 0
    x = y = 0; nsteps = 0
    while nsteps < step_cap:
        nsteps += 1
        act = L.policy((op, last, a_bl, b_bl, int(c != 0), has_out))
        if act is None: return None
        if act == HALT: return out, c
        if act == READ:
            a_bl = int(i >= len(A)); b_bl = 0 if op == MUL else int(i >= len(B))
            x = 0 if a_bl else A[i]
            y = B[0] if op == MUL else (0 if b_bl else B[i])
        elif act == FACT:
            cc = 0 if drop_carry else c
            r = L.fact(op, x, y, cc, derive)
            if r is None: return None
            o, c = r; has_out = int(o is not None); pend = o
            if flip_carry_at is not None and i == flip_carry_at and op == ADD: c = 1 - c
        elif act == WRITE:
            out.append(pend)
        elif act == ADV:
            i += 1; has_out = 0
        last = act
    return None

def train(op_list, n_demo, seed, max_nd=3, with_succ=True):
    L = Learner(); r = Rng(seed)
    for _ in range(n_demo):
        op = op_list[r.next(len(op_list))]
        na, nb = 1 + r.next(max_nd), 1 + r.next(max_nd)
        if op == MUL: a, b = sample_pair(r, na, 1, False)[0], 1 + r.next(9)
        else:
            a, b = sample_pair(r, na, nb, False)
            if op == SUB and a < b: a, b = b, a
        L.watch(op, digits(a), [b] if op == MUL else digits(b))
    if with_succ: L.watch_counting()
    return L

def answer(L, op, a, b, derive=True, **kw):
    r = run(L, op, digits(a), [b] if op == MUL else digits(b), derive, **kw)
    if r is None: return None
    out, c = r
    return c if op == CMP else undigits(out)

def truth(op, a, b):
    return {ADD: a + b, SUB: a - b, MUL: a * b, CMP: (1 if a > b else 2 if a < b else 0)}[op]

def eval_len(L, op, nd, n, seed, derive=True, test_split=True, **kw):
    r = Rng(seed); ok = 0
    for _ in range(n):
        if op == MUL:
            a = sample_pair(r, nd, 1, test_split)[0]; b = 1 + r.next(9)
        else:
            a, b = sample_pair(r, nd, nd, test_split)
            if op == SUB and a < b: a, b = b, a
        ok += answer(L, op, a, b, derive, **kw) == truth(op, a, b)
    return ok / n

# =========================== experiments ===========================
def T1():
    print('== T1 declarative fact table: held-out entries (add, 200 entries (x,y,c)) ==')
    ent = [(x, y, c) for x in range(10) for y in range(10) for c in (0, 1)]
    r = Rng(11); test = [e for e in ent if r.next(10) < 3]; tr = [e for e in ent if e not in set(test)]
    L = Learner()
    for (x, y, c) in tr: L.facts[(ADD, x, y, c)] = true_fact(ADD, x, y, c)
    L.watch_counting()
    lk = sum(L.fact(ADD, *e, False) == true_fact(ADD, *e[:3]) for e in test) / len(test)
    dv = sum(L.fact(ADD, *e, True) == true_fact(ADD, *e[:3]) for e in test) / len(test)
    print(f'  train {len(tr)}  held-out {len(test)}')
    print(f'  pure lookup (memorize)          held-out {100*lk:.0f}%')
    print(f'  + successor counting (given procedure) held-out {100*dv:.0f}%')
    from sklearn.neural_network import MLPClassifier
    def enc(es): 
        X = np.zeros((len(es), 22)); 
        for i, (x, y, c) in enumerate(es): X[i, x] = 1; X[i, 10 + y] = 1; X[i, 20 + c] = 1
        return X
    Y = lambda es: [true_fact(ADD, *e)[0] * 2 + true_fact(ADD, *e)[1] for e in es]
    clf = MLPClassifier((64,), max_iter=3000, random_state=0).fit(enc(tr), Y(tr))
    print(f'  MLP on same split               train {100*clf.score(enc(tr),Y(tr)):.0f}%  held-out {100*clf.score(enc(test),Y(test)):.0f}%')

def T2():
    print('== T2 multi-digit addition: learned procedure vs baselines (unseen operand pairs) ==')
    L = train([ADD], 200, 5)
    print(f'  learned policy entries {len(L.pol)}, facts {len(L.facts)}/200')
    for nd in (1, 2, 3):
        print(f'  {nd} digits (held-out pairs)  procedure {100*eval_len(L, ADD, nd, 300, 100+nd):.0f}%')
    for nd in (4, 6, 10, 20, 50):
        print(f'  {nd:2d} digits (length-gen)     procedure {100*eval_len(L, ADD, nd, 300, 200+nd, test_split=False):.0f}%')
    # baselines
    from sklearn.neural_network import MLPClassifier
    def pairs(n, seed, want_test):
        r = Rng(seed); out = []
        for _ in range(n): out.append(sample_pair(r, 1 + r.next(3), 1 + r.next(3), want_test))
        return out
    def enc(ps):
        X = np.zeros((len(ps), 60))
        for i, (a, b) in enumerate(ps):
            for j, d in enumerate(digits(a) + [0] * (3 - len(digits(a)))): X[i, j*10 + d] = 1
            for j, d in enumerate(digits(b) + [0] * (3 - len(digits(b)))): X[i, 30 + j*10 + d] = 1
        return X
    trp, tep = pairs(3000, 7, False), pairs(500, 8, True)
    Ys = lambda ps: np.array([digits(a + b) + [0] * (4 - len(digits(a + b))) for a, b in ps])
    clfs = [MLPClassifier((128,), max_iter=500, random_state=0).fit(enc(trp), Ys(trp)[:, k]) for k in range(4)]
    def acc(ps):
        P = np.stack([c.predict(enc(ps)) for c in clfs], 1); return float(np.mean((P == Ys(ps)).all(1)))
    print(f'  B1 direct MLP (3000 pairs, 3-digit window)  train {100*acc(trp):.0f}%  held-out 1-3d {100*acc(tep):.0f}%  4+ digits: cannot be encoded (0%)')
    # B2: gradient-trained step function inside the same loop
    ent = [(x, y, c) for x in range(10) for y in range(10) for c in (0, 1)]
    def e22(es):
        X = np.zeros((len(es), 22))
        for i, (x, y, c) in enumerate(es): X[i, x] = 1; X[i, 10 + y] = 1; X[i, 20 + c] = 1
        return X
    Yf = [true_fact(ADD, *e)[0] * 2 + true_fact(ADD, *e)[1] for e in ent]
    net = MLPClassifier((64,), max_iter=3000, random_state=0).fit(e22(ent), Yf)
    class NetL(Learner):
        def fact(self, op, x, y, c, derive):
            p = int(net.predict(e22([(x, y, c)]))[0]); return p // 2, p % 2
    N = NetL(); N.pol = L.pol
    for nd in (3, 10, 50):
        print(f'  B2 gradient step-net in the loop, {nd:2d} digits: {100*eval_len(N, ADD, nd, 200, 300+nd, test_split=False):.0f}%')
    print('  B3 pair lookup: held-out 0% by construction (exact pair never seen)')
    print('  upper bound (hardcoded int add): 100%')
    print('  -- demos needed (coverage sweep), 6-digit accuracy; mean of 5 seeds --')
    for nd_ in (1, 2, 3, 5, 10, 20, 50, 200):
        res = {}
        for derive in (False, True):
            res[derive] = np.mean([eval_len(train([ADD], nd_, 40 + s), ADD, 6, 100, 900 + s, derive, False) for s in range(5)])
        print(f'    {nd_:3d} demo traces: lookup-only {100*res[False]:3.0f}%   +successor derivation {100*res[True]:3.0f}%')

def T3():
    print('== T3 other procedures, same machine, learned from demonstration traces; 2-3 digits = held-out pairs, 6+ = length generalization ==')
    for nd_, derive in ((1200, False), (1200, True), (8000, False)):
        L = train([ADD, SUB, MUL, CMP], nd_, 9)
        nf = {o: sum(1 for k in L.facts if k[0] == o) for o in range(4)}
        print(f'  -- {nd_} traces, derivation {"on" if derive else "off"}; policy entries {len(L.pol)}; facts stored add {nf[0]}/200 sub {nf[1]}/200 mul {nf[2]}/900 cmp {nf[3]}/300')
        for op in (ADD, SUB, MUL, CMP):
            row = [f'{nd}d:{100*eval_len(L, op, nd, 200, 400+nd+10*op, derive, test_split=(nd<=3)):.0f}%' for nd in (2, 3, 6, 12, 30)]
            print(f'     {OPN[op]:4s} ' + '  '.join(row))

def T5():
    print('== T5 ablations (addition, trained on 200 traces) ==')
    L = train([ADD], 200, 5)
    print(f'  intact: 6d {100*eval_len(L, ADD, 6, 300, 1, test_split=False):.0f}%')
    r = Rng(77)
    tot = loc = wrong = 0
    for _ in range(300):
        a, b = sample_pair(r, 6, 6, False)
        got = answer(L, ADD, a, b, drop_carry=True)
        t = a + b
        ok = got == t; wrong += not ok
        # carries exist in operands? failure should happen iff some carry is generated
        carries = any(x + y + 0 >= 10 for x, y in zip(digits(a), digits(b)))
        tot += 1; loc += (not ok) == carries
    print(f'  drop carry rule: wrong on {100*wrong/tot:.0f}% ; failure iff operands generate a carry in {100*loc/tot:.0f}% of cases (localized, predictable)')
    r = Rng(78); first_ok = 0; n = 0
    for _ in range(300):
        a, b = sample_pair(r, 8, 8, False); k = r.next(8)
        got = answer(L, ADD, a, b, flip_carry_at=k); t = a + b
        gd, td = digits(got), digits(t)
        diff = [i for i in range(min(len(gd), len(td))) if gd[i] != td[i]]
        n += 1; first_ok += bool(diff) and diff[0] == k + 1
    print(f'  corrupt carry register at step k: first wrong digit is exactly k+1 in {100*first_ok/n:.0f}% of cases (error traceable to the corrupted step)')

# ---------------- T4 word problems ----------------
TRAIN_NAMES = ['Tom', 'Mia', 'Ben', 'Lek', 'Nok']; TEST_NAMES = ['Ann', 'Pim', 'Joe', 'Sam', 'Dao']
TRAIN_OBJ = ['apples', 'books', 'coins', 'marbles', 'stickers']; TEST_OBJ = ['pens', 'cards', 'shells', 'beads', 'kites']
ADD_V = ['gets', 'finds', 'buys', 'wins']; SUB_V = ['loses', 'eats', 'sells', 'gives']
NEW_ADD_V = ['receives', 'collects', 'earns', 'gains']; NEW_SUB_V = ['drops', 'spends', 'donates', 'burns']

def gen_wp(r, names, objs, addv, subv):
    nm, ob = names[r.next(5)], objs[r.next(5)]
    a = 10 + r.next(990)
    ops = [r.next(2), r.next(2)]; tot = a; text = [f'{nm} has {a} {ob}.']; seq = []
    for o in ops:
        v = (addv if o == 0 else subv)[r.next(4)]
        n = 1 + r.next(min(500, max(tot, 1)) if o == 1 else 500)
        text.append(f'{nm} {v} {n} {"more " if o == 0 else ""}{ob}.')
        tot = tot + n if o == 0 else tot - n; seq.append((v, n))
    text.append(f'How many {ob} does {nm} have now?')
    return ' '.join(text), a, seq, tot

def trigrams(w): w = f'^{w}$'; return {w[i:i+3] for i in range(len(w) - 2)}

class WP:
    def __init__(self, L):
        self.L = L; self.verbs = {}
    def learn(self, v, op): self.verbs[v] = op
    def op_of(self, v):
        if v in self.verbs: return self.verbs[v]
        t = trigrams(v)
        best = max(self.verbs, key=lambda u: (len(t & trigrams(u)) / len(t | trigrams(u)), u))
        return self.verbs[best]
    def solve(self, text):
        sents = [s for s in text.split('.') if s.strip()][:3]
        a = int(sents[0].split()[2]); tot = a
        for s in sents[1:]:
            tk = s.split(); v = tk[1]; n = int(tk[2])
            op = ADD if self.op_of(v) == 0 else SUB
            tot = answer(self.L, op, tot, n)
            if tot is None: return None
        return tot

def T4():
    print('== T4 two-step word problems (fixed template; parser GIVEN, verb->op LEARNED, arithmetic via learned procedures) ==')
    L = train([ADD, SUB], 400, 21); w = WP(L)
    for v in ADD_V: w.learn(v, 0)
    for v in SUB_V: w.learn(v, 1)
    def score(names, objs, av, sv, seed, n=300):
        r = Rng(seed); ok = ad = 0
        for _ in range(n):
            t, a, seq, tot = gen_wp(r, names, objs, av, sv)
            ok += w.solve(t) == tot
            ok2 = a
            for v, k in seq: ok2 += k if (v in av) else -k   # "always add" heuristic baseline ignores verbs
            ad += (a + sum(k for _, k in seq)) == tot
        return ok / n, ad / n
    s1 = score(TRAIN_NAMES, TRAIN_OBJ, ADD_V, SUB_V, 31)
    s2 = score(TEST_NAMES, TEST_OBJ, ADD_V, SUB_V, 32)
    s3 = score(TEST_NAMES, TEST_OBJ, NEW_ADD_V, NEW_SUB_V, 33)
    print(f'  seen names/objects, seen verbs (new numbers)      {100*s1[0]:.0f}%   (always-add baseline {100*s1[1]:.0f}%)')
    print(f'  NEW names/objects, seen verbs                      {100*s2[0]:.0f}%   (always-add baseline {100*s2[1]:.0f}%)')
    print(f'  NEW names/objects, UNSEEN verbs (char-trigram NN)  {100*s3[0]:.0f}%   (always-add baseline {100*s3[1]:.0f}%)')
    # what the verb map does on unseen verbs
    rows = [(v, w.op_of(v), 0) for v in NEW_ADD_V] + [(v, w.op_of(v), 1) for v in NEW_SUB_V]
    print('  unseen verb mapping: ' + ', '.join(f'{v}->{"add" if o==0 else "sub"}{"" if o==t else " (WRONG)"}' for v, o, t in rows))

if __name__ == '__main__':
    which = sys.argv[1:] or ['T1', 'T2', 'T3', 'T4', 'T5']
    for t in which: globals()[t](); print()
