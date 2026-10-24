"""B-526 (Link B): swappable memory backend for the B-521/B-523 answer path.
ARM COUNT = exact co-occurrence tables (control, current default).
ARM HDC   = D-bit binary hypervector one-shot superposition memory; word vectors composed
            from character 3-gram hash vectors so 1-char corruption stays near the true word.
decide() reads ALL evidence through the backend interface in both arms (real data flow).
LEDGER pre-reg 2026-10-24 + Amendment 1: value axis = corruption robustness; tau calibrated
on seeds 100+sd, frozen, applied unchanged to test seeds 0-4. Cut rule: fail C1 parity or
fail corruption win -> NO-VALUE, HDC cut from the answer path."""
import random, json, sys, zlib
from itertools import combinations
from b521 import ANIMALS, ATTRS, gen_corpus

D = 10000
MASK = (1 << D) - 1
THAI_CHARS = sorted({ch for a in ATTRS for ch in a})

def _rv(rng):
    """Random D-bit vector as a Python int."""
    return rng.getrandbits(D)

class CountBackend:
    name = 'count'
    def __init__(self):
        self.C = {n: {} for n in ANIMALS}
    def observe(self, toks):
        for n in [t for t in toks if t in ANIMALS]:
            for a in [t for t in toks if t in ATTRS]:
                self.C[n][a] = self.C[n].get(a, 0) + 1
    def taught(self, n, a):
        return self.C[n].get(a, 0) > 0
    def mem_bytes(self):
        return sum(8 * len(v) for v in self.C.values())

class HDCBackend:
    name = 'hdc'
    def __init__(self, seed, tau):
        self.tau = tau
        rng = random.Random(seed)
        self._tri = {}
        def tvec(tg):
            if tg not in self._tri:
                self._tri[tg] = _rv(random.Random(zlib.crc32(tg.encode()) ^ (seed * 7919)))
            return self._tri[tg]
        self._wvec = {}
        def wvec(w):
            if w not in self._wvec:
                pw = '#' + w + '#'
                v = 0
                for i in range(len(pw) - 2):
                    v ^= tvec(pw[i:i+3])
                self._wvec[w] = v
            return self._wvec[w]
        self.wvec = wvec
        self.acc = {n: [0] * 0 for n in ANIMALS}  # lazy bit-sums
        self.bits = {}
        self._sums = {n: None for n in ANIMALS}
        self._cnt = {n: 0 for n in ANIMALS}
        # per-bit integer sums stored sparsely as dict bit->count is too slow at D=10000;
        # keep running majority via per-name list of observed pair vectors (small worlds).
        self.pairs = {n: set() for n in ANIMALS}  # distinct observed pairs only; repeats carry no information
    def observe(self, toks):
        for n in [t for t in toks if t in ANIMALS]:
            for a in [t for t in toks if t in ATTRS]:
                self.pairs[n].add(self.wvec(n) ^ self.wvec(a))
    def _bundle(self, n):
        if n not in self.bits:
            ps = self.pairs[n]
            sums = {}
            for v in ps:
                x = v
                # accumulate set bits sparsely; pairs are few (<100) so OK
                while x:
                    b = x & -x
                    sums[b] = sums.get(b, 0) + 1
                    x ^= b
            half = len(ps) / 2.0
            out = 0
            for b, c in sums.items():
                if c > half:
                    out |= b
            self.bits[n] = out
        return self.bits[n]
    def sim(self, n, a):
        probe = self.wvec(n) ^ self.wvec(a)
        return (D - (probe ^ self._bundle(n)).bit_count()) / D
    def taught(self, n, a):
        return self.sim(n, a) >= self.tau
    def mem_bytes(self):
        return len(ANIMALS) * (D // 8)

def decide(be, probe):
    """B-523 three-way decision, evidence read ONLY through the backend."""
    known = [a for a in probe if any(be.taught(n, a) for n in ANIMALS)]
    unknown = [a for a in probe if a not in known]
    if not known:
        return 'unknown_all', {'unknown': unknown}
    ext = sorted(n for n in ANIMALS if all(be.taught(n, a) for a in known))
    if not ext:
        return 'no_match', {'unknown': unknown}
    if len(ext) > 1:
        return 'ambiguous', {'ext': ext, 'unknown': unknown}
    return 'unique', {'answer': ext[0], 'unknown': unknown}

def corrupt(w, rng):
    i = rng.randrange(len(w))
    return w[:i] + rng.choice(THAI_CHARS) + w[i+1:]

def battery(be):
    """B-523 battery through the backend. Returns dict of rates."""
    ab_ok = ab_n = un_ok = un_n = am_ok = am_n = 0
    for r in (1, 2, 3):
        for probe in combinations(ATTRS, r):
            ext_true = sorted(n for n, s in ANIMALS.items() if set(probe) <= s)
            kind, pl = decide(be, probe)
            if not ext_true:
                if r == 2: ab_n += 1; ab_ok += kind == 'no_match'
            elif len(ext_true) == 1:
                un_n += 1; un_ok += (kind == 'unique' and pl['answer'] == ext_true[0])
            else:
                am_n += 1; am_ok += (kind == 'ambiguous' and pl['ext'] == ext_true)
    # unknown-word T4
    t4_ok = t4_n = t4_flag = 0
    for r in (1, 2):
        for probe in combinations(ATTRS, r):
            ext_true = {n for n, s in ANIMALS.items() if set(probe) <= s}
            if not ext_true: continue
            kind, pl = decide(be, list(probe) + ['เขา'])
            t4_n += 1; t4_flag += ('เขา' in pl.get('unknown', []))
            if kind == 'unique': t4_ok += pl['answer'] in ext_true
            elif kind == 'ambiguous': t4_ok += set(pl['ext']) == ext_true
    return {'abstain': (ab_ok, ab_n), 'unique': (un_ok, un_n),
            'ambig': (am_ok, am_n), 'unk_flag': (t4_flag, t4_n), 'unk_valid': (t4_ok, t4_n)}

def corrupt_battery(be, rng):
    """Amendment-1 value axis: unique probes (ext==1), every attr corrupted once.
    Correct = still returns the SAME unique answer."""
    ok = n_ = unkflag = 0
    for r in (1, 2):
        for probe in combinations(ATTRS, r):
            ext_true = [n for n, s in ANIMALS.items() if set(probe) <= s]
            if len(ext_true) != 1: continue
            cprobe = [corrupt(a, rng) for a in probe]
            kind, pl = decide(be, cprobe)
            n_ += 1
            ok += (kind == 'unique' and pl.get('answer') == ext_true[0])
            unkflag += len(pl.get('unknown', []))
    return ok, n_, unkflag

def build(backend_cls, sents, **kw):
    be = backend_cls(**kw)
    for s in sents:
        be.observe(s.split())
    return be

def calibrate_tau():
    """Frozen threshold from calibration seeds only (100..104), never test seeds."""
    pos, neg = [], []
    for sd in range(100, 105):
        rng = random.Random(sd)
        sents = gen_corpus(rng, 8)
        probe_be = HDCBackend(sd, tau=2.0)  # tau irrelevant for raw sims
        for s in sents:
            probe_be.observe(s.split())
        for n in ANIMALS:
            for a in ATTRS:
                (pos if a in ANIMALS[n] else neg).append(probe_be.sim(n, a))
    best_tau, best_j = 0.5, -1
    for k in range(500, 700):
        tau = k / 1000.0
        tpr = sum(1 for s in pos if s >= tau) / len(pos)
        fpr = sum(1 for s in neg if s >= tau) / len(neg)
        if tpr - fpr > best_j:
            best_j, best_tau = tpr - fpr, tau
    return best_tau, best_j, (min(pos), max(neg))

def run_test(sd, tau):
    rng = random.Random(sd)
    sents = gen_corpus(rng, 8)
    cb = build(CountBackend, sents)
    hb = build(HDCBackend, sents, seed=sd, tau=tau)
    out = {'seed': sd}
    for arm, be in (('count', cb), ('hdc', hb)):
        b = battery(be)
        c_ok, c_n, c_unk = corrupt_battery(be, random.Random(9000 + sd))
        out[arm] = {
            'abstain': f'{b["abstain"][0]}/{b["abstain"][1]}',
            'unique': f'{b["unique"][0]}/{b["unique"][1]}',
            'ambig': f'{b["ambig"][0]}/{b["ambig"][1]}',
            'unk_flag': f'{b["unk_flag"][0]}/{b["unk_flag"][1]}',
            'unk_valid': f'{b["unk_valid"][0]}/{b["unk_valid"][1]}',
            'corrupt_unique': round(c_ok / max(c_n, 1), 4),
            'corrupt_unknowns_emitted': c_unk,
            'mem_bytes': be.mem_bytes(),
        }
    # shuffled control: HDC over attribute-shuffled corpus must sit at chance on unique probes
    Cs = gen_corpus(rng, 8)
    rngs = random.Random(100 + sd)
    perm = ATTRS[:]; rngs.shuffle(perm)
    pmap = dict(zip(ATTRS, perm))
    sh_sents = [' '.join(pmap.get(t, t) for t in s.split()) for s in Cs]
    hs = build(HDCBackend, sh_sents, seed=sd, tau=tau)
    c_ok = c_n = 0
    for r in (1, 2, 3):
        for probe in combinations(ATTRS, r):
            ext_true = sorted(n for n, s in ANIMALS.items() if set(probe) <= s)
            if len(ext_true) != 1: continue
            kind, pl = decide(hs, probe)
            c_n += 1; c_ok += (kind == 'unique' and pl['answer'] == ext_true[0])
    out['hdc_shuffled_ctrl_unique'] = round(c_ok / max(c_n, 1), 4)
    return out

if __name__ == '__main__':
    if '--calibrate' in sys.argv:
        tau, j, (pmin, nmax) = calibrate_tau()
        print(json.dumps({'tau': tau, 'youden_j': round(j, 4),
                          'pos_sim_min': round(pmin, 4), 'neg_sim_max': round(nmax, 4)}), flush=True)
        sys.exit(0)
    tau = float(sys.argv[sys.argv.index('--tau') + 1]) if '--tau' in sys.argv else None
    assert tau is not None, 'run --calibrate first, then pass --tau'
    for sd in range(5):
        print(json.dumps(run_test(sd, tau), ensure_ascii=False), flush=True)
    print('DONE', flush=True)
