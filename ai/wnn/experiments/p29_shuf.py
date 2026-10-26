"""P29 shuffled-order control: same as run3 training but every A line's words are shuffled.
Association (comp) should survive; pair-bigram production order must collapse."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import baby5 as m
import random
def run(seed, f, pa, pb, covered):
    rng = random.Random(2000 + seed); w = m.WorldC(rng, covered); b = m.Baby5P()
    wr = random.Random(999)
    for day in range(5):
        for _ in range(100):
            sc = w.scene(); pres = w.tokens(sc)
            for _ in range(rng.choice((2, 3, 4))):
                if rng.random() < f:
                    line = pa(rng, sc); wr.shuffle(line); b.hear(line, pres)
                else:
                    b.hear(pb(rng), pres)
    prng = random.Random(77); bg_ok = 0
    for _ in range(20):
        e, a = prng.choice(covered)
        bf, br = b.bg.get((m.WE[e], m.WA[a]), 0), b.bg.get((m.WA[a], m.WE[e]), 0)
        if bf > br: bg_ok += 1
    comp_ok, comp_n = 0, 0
    crng = random.Random(88)
    for _ in range(200):
        e, a = crng.choice(covered)
        for wd, tt in ((m.WE[e], m.TOK[('E', e)]), (m.WA[a], m.TOK[('A', a)])):
            av = b.assoc.get(wd, {})
            if av:
                comp_n += 1
                comp_ok += max(av.items(), key=lambda kv: kv[1])[0] == tt
    return bg_ok, comp_ok / comp_n
pa, pb, covered = m.load_llm_pools('pools.json')
for f in (1.0, 0.5):
    for seed in range(3):
        bg, comp = run(seed, f, pa, pb, covered)
        print(f'SHUFFLED f={f} seed{seed}: prod_bg={bg}/20 comp={comp:.2f}', flush=True)
