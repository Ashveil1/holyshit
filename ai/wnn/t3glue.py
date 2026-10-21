"""B-184: paraphrase teaching for 2-step glue words. Train TwoStep on n=1000 same-phrasing
sentences, then TEACH arm adds 4 labelled sentences: wh=0 sentences with the connector swapped
for each new connector (familiar frames, new glue word). Eval: wh=1 (new connectors+frames).
Baseline: P16 .44 (n=1000). Success: > .6. 5 seeds, 300 eval rows/seed."""
import random
from text2prog2 import TwoStep, two_step, CONN
def teach_rows(rng):
    rows = []
    for newc in CONN[1]:
        for _ in range(200):
            _, t, a, info = two_step(rng, 0, False)
            if info is None or not info[1]: continue
            nl, conn = info; toks = t.split()
            t2 = ' '.join(toks[:nl] + newc.split() + toks[nl + len(conn.split()):])
            rows.append((t2, a)); break
    return rows
def arm(sd, teach):
    rng = random.Random(sd)
    M = TwoStep(); M.fit([(t, a) for _, t, a, _ in (two_step(rng, 0, False) for _ in range(1000))])
    if teach: M.fit(teach_rows(rng))
    r = random.Random(100 + sd); ok = 0
    for _ in range(300):
        _, t, a, _ = two_step(r, 1, True)
        try: ok += M.solve(t)[0] == a
        except Exception: pass
    return ok / 300
if __name__ == '__main__':
    for teach in (False, True):
        sc = [arm(sd, teach) for sd in range(5)]
        print(f'teach={teach}: new connectors acc {sum(sc)/5:.2f} [{min(sc):.2f}-{max(sc):.2f}]', flush=True)
