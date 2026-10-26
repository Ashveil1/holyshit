"""B-242: episodic recall of a named fact after 1000 distractor facts (HDC, XOR binding, random codes).
Recall the FIRST fact after writing N more. Baseline: recall with no distractors. dims 4096/16384, 5 seeds.
Success: recall unchanged."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import numpy as np
import t5hdc
from t5hdc import codebook, clean
def run(D, distract, sd):
    t5hdc.D = D
    C = codebook(2 + 2 * 1100, 'random', np.random.default_rng(sd))
    M = np.zeros(D, np.int64)
    M += C[0] * C[1]  # the named fact: key0 -> value1
    for i in range(distract): M += C[2 + 2 * i] * C[3 + 2 * i]
    M = np.sign(M)
    v = clean(M * C[0], C[1:])
    return np.array_equal(v, C[1])
for D in (4096, 16384):
    for distract in (0, 100, 1000):
        a = [run(D, distract, sd) for sd in range(5)]
        print(f'dim {D:5d} distractors {distract:4d}: first-fact recall {sum(a)/5:.2f}', flush=True)
