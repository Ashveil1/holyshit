"""BABY3C: offline replay of the P27h control arms over ONE pre-generated dialogue set per seed.
Arms: 'overhear' (baby only hears; never speaks; no reward) and 'rewonly' (baby hears + produces internally +
gets the scalar reward, but caregivers are NEVER told - no echo in the dialogue). Same learner/criterion.
Usage: python3 baby3c.py SEED < dialogue_array_file (JSON array of 300 strings, one per scene)"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from baby3 import SIT, Baby
from baby3h import gen_day, evaluate
def run(arm, seed, lines, pool=None, pool_rng=None, full=False):
    b = Baby(); n = 0; out = []; first = None
    from baby3h import SIT_EN
    for d in range(1, 6):
        day = gen_day(seed, d)
        for (s, present) in day:
            if pool is not None:
                key = ' + '.join(sorted(SIT_EN[o] for o in present))
                arr = pool[key]; line = arr[pool_rng.randrange(len(arr))]
            else:
                line = lines[n]
            n += 1; present = set(present)
            words = [w.strip() for w in line.replace('A:', ' ').replace('B:', ' ').replace('|', ' ').split() if w.strip()]
            b.hear(words, present)
            if arm == 'rewonly':
                w = b.say(present)
                if w is not None:
                    b.spoke += 1; b.reward(w, present, w == SIT[s])
        mae, non, hit = evaluate(b, seed)
        out.append(f'{arm} seed{seed} day {d}: mae {mae:.2f} non {non:.2f} all6 {hit:.2f} spoke {b.spoke} heard {b.heard}')
        if mae >= 0.8 and non <= 0.2 and not full:
            out.append(f'{arm} seed{seed}: FIRST WORD DAY {d}'); break
        elif mae >= 0.8 and non <= 0.2 and first is None:
            first = d
    if full and first is not None:
        out.append(f'{arm} seed{seed}: FIRST WORD DAY {first}')
    return out
if __name__ == '__main__':
    seed = int(sys.argv[1]); full = len(sys.argv) > 2 and sys.argv[2] == 'full'
    data = json.load(sys.stdin)
    if isinstance(data, dict):  # pool mode: {type: [lines]}
        import random
        for arm in ('overhear', 'rewonly'):
            rng = random.Random(7000 + seed)  # same sampling order for both arms
            for l in run(arm, seed, None, pool=data, pool_rng=rng, full=full): print(l, flush=True)
    else:
        print(f'{len(data)} dialogue lines')
        for arm in ('overhear', 'rewonly'):
            for l in run(arm, seed, data, full=full): print(l, flush=True)
