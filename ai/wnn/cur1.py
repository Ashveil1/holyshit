"""Curriculum level 1: learn base skills from examples with the exhaustive search over MANY random training sets
(seeds), raw bank vs library bank. python3 cur1.py BANK(raw7|lib6) TASKS SEEDS"""
import sys, time, random, pickle, induce as I
bank_name, tasks, seeds = sys.argv[1], sys.argv[2].split(','), int(sys.argv[3])
maxs, lib = (7, ()) if bank_name == 'raw7' else (6, (('%', '10'), ('//', '10')))
bank = I.build(maxs, lib=lib); out = {}
HARD = ('sub', 'compare')
for task in tasks:
    ok = found = 0; ts = []; progs = []
    for s in range(seeds):
        rng = random.Random(500 + s); hard = task in HARD
        train = [I.mk(task, rng, rng.choice([1, 2, 3, 4] if hard else [1, 2, 3])) for _ in range(40 if hard else 20)]
        t0 = time.time(); best = I.search(train, bank, maxs); ts.append(time.time() - t0)
        if not best: continue
        found += 1; rng2 = random.Random(77); good = True
        for n in (4, 6, 10, 20, 50):
            for _ in range(100):
                xs, ys, o = I.mk(task, rng2, n)
                if I.run(best[1], xs, ys) != o: good = False; break
            if not good: break
        ok += good; progs.append((good, best[2], best[1][:3]))
    print(f'[{bank_name}] {task:8s} found {found}/{seeds}  correct at 4-50 digits {ok}/{seeds}  search time mean {sum(ts)/len(ts):.1f}s max {max(ts):.1f}s', flush=True)
    out[task] = [(g, src, (rd, wr, mode)) for g, src, (rd, wr, mode) in progs]
pickle.dump(out, open(f'/tmp/cur1_{bank_name}.pkl', 'wb'))
