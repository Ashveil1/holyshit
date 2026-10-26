"""P30 (baby6.py): vocative / call-consequence learning. Ash's question: how does the baby know
"แม่" is a CALL? Design (pre-registered with owner): bare-name lines predict the NAMED caregiver
turning on the NEXT tick (selective response); referential mentions don't. Learner: Baby5 grounding
+ temporal-shift Hebbian channel (prev-line bare word <-> current event tokens). Events opaque tokens.
V1 comprehension >=.9 (f=1.0); V2 instrumental production >=.9; V3 shuffled-consequence control <=.6/.5."""
import random, json, sys
from collections import defaultdict
from baby5 import WorldC, Baby5, load_llm_pools, WE, WA, TOK, ENT, ACT, VALID
CARE = ['mae', 'pho']  # caregiver entity names
EVT = {'turn_mae': 'V0', 'turn_pho': 'V1', 'appr_mae': 'V2', 'appr_pho': 'V3'}
class Baby6(Baby5):
    def __init__(s):
        super().__init__()
        s.temp = defaultdict(lambda: defaultdict(float))  # bare word -> event token assoc
    def hear_call(s, bare_word, events_next):
        """temporal channel: bare call word vs NEXT tick's event tokens"""
        for ev in EVT.values():
            s.temp[bare_word][ev] += 1.0 if ev in events_next else -0.25
def run_v(seed, f, pool_a, pool_b, covered, days=5, scenes_per_day=100, shuffle_cons=False):
    rng = random.Random(3000 + seed); w = WorldC(rng, covered); b = Baby6()
    calls = []   # (bare_word) calls made this tick; events land next tick
    srng = random.Random(4242)
    pending_events = set()
    for day in range(days):
        for _ in range(scenes_per_day):
            sc = w.scene(); pres = set(w.tokens(sc)) | pending_events
            pending_events = set()
            care_present = CARE[:] if rng.random() < 0.6 else [rng.choice(CARE)]
            # ensure scene tokens include present caregivers (world may show other entities too)
            for c in care_present: pres.add(TOK[('E', c)])
            nlines = rng.choice((2, 3, 4))
            for _ in range(nlines):
                b.hear(pool_a(rng, sc) if rng.random() < f else pool_b(rng), pres)
            # call event in two-caregiver scenes, p=.5
            new_events = set()
            if len(care_present) == 2 and rng.random() < 0.5:
                caller, callee = rng.sample(care_present, 2)
                bare = WE[callee]
                b.hear([bare], pres)  # the call line itself is heard
                new_events.add(EVT['turn_' + callee])
                if rng.random() < 0.5: new_events.add(EVT['appr_' + callee])
                calls.append(bare)
            elif rng.random() < 0.05:  # spontaneous noise turn
                new_events.add(EVT['turn_' + rng.choice(CARE)])
            pending_events = new_events
            # pair the call with the events it caused (they appear on the next tick)
            if calls:
                b.hear_call(calls[-1], new_events)
                calls = []  # one call per scene max
    # shuffle control: permute temp rows against event columns
    if shuffle_cons:
        words = list(b.temp.keys()); evs = list(EVT.values())
        perm = evs[:]; srng.shuffle(perm)
        for wd in words:
            row = b.temp[wd]
            b.temp[wd] = {perm[i]: row[evs[i]] for i in range(len(evs))}
    # V1: after bare name, predicted turn argmax correct?
    v1_ok, v1_n = 0, 0
    for c in CARE:
        row = b.temp.get(WE[c], {})
        if row:
            v1_n += 1
            pred = max((t for t in ('V0', 'V1')), key=lambda t: row.get(t, 0.0))
            v1_ok += pred == EVT['turn_' + c]
    # V2: instrumental production - word with strongest assoc to TURN(target)
    v2_ok, v2_n = 0, 0
    for c in CARE:
        ev = EVT['turn_' + c]
        best, bs = None, 0.0
        for wd in b.assoc:
            row = b.temp.get(wd, {})
            sc_ = row.get(ev, 0.0) - 0.5 * sum(row.get(o, 0.0) for o in ('V0', 'V1') if o != ev)
            if sc_ > bs: best, bs = wd, sc_
        v2_n += 1; v2_ok += best == WE[c]  # best=None (no positive contingency) scores False
    return v1_ok, v1_n, v2_ok, v2_n, {wd: {k: round(v, 1) for k, v in b.temp[wd].items()} for wd in list(b.temp)[:6]}
if __name__ == '__main__':
    pa, pb, covered = load_llm_pools(sys.argv[1])
    for mode, sc in (('NORMAL', False), ('SHUFFLED-CONS', True)):
        for f in (1.0, 0.2):
            for seed in range(3):
                v1o, v1n, v2o, v2n, dump = run_v(seed, f, pa, pb, covered, shuffle_cons=sc)
                print(f'{mode} f={f} seed{seed}: V1={v1o}/{v1n} V2={v2o}/{v2n} temp_sample={json.dumps(dump, ensure_ascii=False)[:200]}', flush=True)
