"""B-519: babbling trajectory - production volume + correct-rate per day + first-grounded day per word.
baby7 run_d dynamics UNCHANGED (passive instrumentation only). LEDGER pre-reg 2026-10-24."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import random, json, sys
from collections import defaultdict
import baby7
from baby7 import WorldC, Baby7, load_llm_pools, WE, WA, WL, P_SCENE, P_GREET, ECHO

def run(seed, pa, pb, covered, days=5, eps_per_day=100, f=1.0):
    rng = random.Random(4000 + seed); w = WorldC(rng, covered); b = Baby7()
    vol = defaultdict(int); appr = defaultdict(list); first_grounded = {}
    for day in range(days):
        for ep in range(eps_per_day):
            sc = w.scene(); pres = set(w.tokens(sc))
            for _ in range(rng.choice((1, 2))):
                b.hear(pa(rng, sc) if rng.random() < f else pb(rng), pres)
            greet = rng.random() < 0.3
            prompt = rng.choice(P_GREET if greet else P_SCENE)
            names = {WE[sc[0]], WA[sc[1]], WL[sc[2]]}
            b.hear(prompt.split(), pres)
            if rng.random() < 0.25 and b.decide_speak_probe(False, rng):
                b.pspeak['noend'] = max(0.01, b.pspeak['noend'] - 0.05)
            if not b.decide_speak_probe(True, rng): continue
            word = b.produce(pres, rng, greet=greet)
            if word is None: continue
            good = (word == ECHO) if greet else (word in names)
            vol[day] += 1; appr[day].append(1.0 if good else 0.0)
            if word not in first_grounded and b.grounded(word):
                first_grounded[word] = day + 1
            reward = 1.0 if good else -1.0
            for t in pres: b.assoc[word][t] += 0.3 * reward
            b.pspeak['end'] = min(0.99, max(0.01, b.pspeak['end'] + 0.05 * reward))
            fb = ('ใช่! ' + word) if good else ('ไม่ใช่ นั่นคือ ' + WE[sc[0]] if not greet else '...')
            b.hear(fb.split(), pres)
    return {'seed': seed,
            'vol': [vol[d] for d in range(days)],
            'rate': [round(sum(appr[d]) / max(1, len(appr[d])), 3) for d in range(days)],
            'first_grounded_day': first_grounded,
            'n_grounded_words': len(first_grounded)}

if __name__ == '__main__':
    pa, pb, covered = load_llm_pools('pools.json')
    for sd in range(5):
        print(json.dumps(run(sd, pa, pb, covered)), flush=True)
    print('DONE', flush=True)
