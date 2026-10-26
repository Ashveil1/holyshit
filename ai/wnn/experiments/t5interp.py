"""B-239: thermometer/DWSA-style encodings for INTERPOLATION on unseen operands (arith).
HDC memory: bind encode(a)*roll,encode(b) -> encode(a+b) for a,b in SEEN values; query with one
unseen operand; exact answer after cleanup over the value codebook. level vs thermo vs random.
P5 E2/E3 predicts ~0 for everyone (exact arithmetic from examples = memorization). dim 4096, 3 seeds."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import numpy as np
import t5hdc
from t5hdc import codebook, clean
t5hdc.D = 4096
def run(enc, sd):
    C = codebook(64, enc, np.random.default_rng(sd))  # values 0..63
    seen = [v for v in range(64) if v % 4 != 3]  # 48 seen values, 16 held out
    rng = np.random.default_rng(sd + 100)
    M = np.zeros(4096, np.int64); pairs = []
    for _ in range(200):
        a = int(rng.choice(seen)); b = int(rng.choice(seen))
        if a + b > 63: continue
        M += C[a] * np.roll(C[b], 1) * 0 + C[a] * np.roll(C[b], 1)  # bind a,(perm b)
        pairs.append((a, b))
    # store sum jointly: bundle bound pair with answer
    Mv = np.zeros(4096, np.int64)
    for a, b in pairs: Mv += C[a] * np.roll(C[b], 1) * C[a + b]  # 3-way bind
    Mv = np.sign(Mv)
    ok = tot = 0
    rng2 = np.random.default_rng(sd + 200)
    for _ in range(300):
        a = int(rng2.choice([v for v in range(64) if v % 4 == 3])); b = int(rng2.choice(seen))
        if a + b > 63: continue
        q = Mv * C[a] * np.roll(C[b], 1)  # unbind with BOTH operands
        v = clean(q, C); ok += np.array_equal(v, C[a + b]); tot += 1
    return ok / max(1, tot)
for enc in ('level', 'thermo', 'random'):
    print(enc, [round(run(enc, sd), 3) for sd in range(3)], flush=True)
