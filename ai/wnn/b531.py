"""B-531: library-reuse value retest with a depth-selected target (LEDGER pre-reg 2026-10-24).
B-530 lesson: new LIB primitives enumerate after the base space - reuse savings are only
measurable on targets whose DIRECT search is deep. Selection rule (fixed): ablated-arm
teach each candidate in order; first with tried >= 100,000 or cap exhaustion is THE target.
Reuse arm then runs once with double+quad (dialog-taught) + sumto (seeded) in LIB."""
import random, json, sys
import cur7 as C
from cur7 import LIB, show_prog, make_fn
from b529 import teach, Teacher, NEW, CAP7
from b530 import as_primitive, accuracy
from b527 import HSMLMemory, derive_skills, load_logged, SKILLS, SKILL_BY_WORD
from b521 import gen_corpus
from b526 import battery

NEW.update({'hexdec': 'สิบหกเท่า', 'sqself': 'กำลังสองบวกตัว', 'oct': 'แปดเท่า'})
CANDS = [('hexdec', lambda x: 16 * x), ('sqself', lambda x: x * (x + 1)), ('oct', lambda x: 8 * x)]
DEEP = 100_000

def fresh_mem():
    mem = HSMLMemory(); mem.skills = derive_skills(load_logged())
    return mem

def teach_primitives(mem, seed=0):
    dok, dlog = teach(mem, Teacher(lambda x: 2 * x), 'double', seed=seed)
    assert dok, 'double teaching failed'
    qok, qlog = teach(mem, Teacher(lambda x: 4 * x), 'quad', seed=seed)
    assert qok, 'quad teaching failed'
    LIB['double'] = as_primitive(mem.skills['double'])
    LIB['quad'] = as_primitive(mem.skills['quad'])
    LIB['sumto'] = as_primitive(mem.skills['sumto'])
    return dlog, qlog

def run_battery():
    out = {'selection': []}
    # ---- target selection: ablated arm only, fixed order ----
    sel = None
    for key, truth in CANDS:
        mem = fresh_mem()
        LIB.pop('double', None); LIB.pop('quad', None); LIB.pop('sumto', None)
        ok, log = teach(mem, Teacher(truth), key)
        rec = {'key': key, 'ok': ok, 'tried': log.get('tried'), 'fail': log.get('fail')}
        out['selection'].append(rec)
        print('select', rec, flush=True)
        if ok and log['tried'] < DEEP:
            continue
        sel = (key, truth, ok, log)
        break
    if sel is None:
        out['verdict_note'] = 'INCONCLUSIVE-DEPTH: all candidates shallow'
        return out, None
    key, truth, aok, alog = sel
    out['target'] = key
    out['c3_ablated'] = {'ok': aok, **{k: v for k, v in alog.items()}}
    # ---- reuse arm: primitives in LIB ----
    mem = fresh_mem()
    teach_primitives(mem)
    rok, rlog = teach(mem, Teacher(truth), key)
    out['c1_reuse'] = {'ok': rok, **rlog}
    print('reuse', rok, rlog, flush=True)
    if rok:
        out['c2_accuracy'] = accuracy(mem, NEW[key], truth)
        sp = show_prog(mem.skills[key][0])
        out['calls_primitive'] = [p for p in ('double', 'quad', 'sumto') if f"'{p}'" in sp]
        out['target_prog'] = sp
        print('C2', out['c2_accuracy'], 'calls', out['calls_primitive'], flush=True)
    # ---- C4 no interference ----
    c4 = {}
    from cur7 import gen as cgen
    for task in SKILLS:
        te = random.Random(1000); okc = n = 0
        for sc in (1, 2, 3, 4):
            for _ in range(40):
                x, y, r = cgen(task, te, sc)
                ans = mem.answer(f'{SKILLS[task]} ของ {x} คืออะไร')
                n += 1
                okc += (ans.get('kind') == 'skill_answer' and ans.get('result') == r)
        c4[task] = f'{okc}/{n}'
    c4['double'] = accuracy(mem, NEW['double'], lambda x: 2 * x)
    c4['quad'] = accuracy(mem, NEW['quad'], lambda x: 4 * x)
    rng = random.Random(0)
    for s in gen_corpus(rng, 8):
        mem.attrs.observe(s.split())
    b = battery(mem.attrs)
    out['c4_seeded'] = c4
    out['c4_attr_battery'] = {k: f'{v[0]}/{v[1]}' for k, v in b.items()}
    print('C4', c4, flush=True)
    # ---- C5 garbage target teacher (primitives in LIB = stronger condition) ----
    mem3 = fresh_mem()
    teach_primitives(mem3)
    grng = random.Random(555); memo = {}
    def gtruth(x):
        if x not in memo: memo[x] = grng.randrange(0, 1000)
        return memo[x]
    gok, glog = teach(mem3, Teacher(gtruth), key)
    out['c5_garbage'] = {'stored': gok, **glog}
    print('C5', gok, glog, flush=True)
    return out, sel

if __name__ == '__main__':
    out, sel = run_battery()
    if sel is None:
        print(json.dumps({'verdict': 'INCONCLUSIVE-DEPTH', **out}, ensure_ascii=False), flush=True)
    else:
        c1 = out['c1_reuse'].get('pairs', 99) <= 20
        acc = out.get('c2_accuracy', '0/40').split('/')[0]
        c2 = acc.isdigit() and int(acc) >= 38
        at = out['c3_ablated'].get('tried') or 0
        rt = out['c1_reuse'].get('tried') or 0
        c3 = out['c1_reuse']['ok'] and (rt * 2 <= at or not out['c3_ablated']['ok'])
        c4 = all(v in ('160/160', '40/40') for v in out['c4_seeded'].values())
        c5 = not out['c5_garbage']['stored']
        verdict = 'PASS' if (c1 and c2 and c3 and c4 and c5) else 'FAIL'
        print(json.dumps({'verdict': verdict, 'c1': c1, 'c2': c2, 'c3': c3, 'c4': c4, 'c5': c5,
                          'tried_ablated': at, 'tried_reuse': rt, **out}, ensure_ascii=False), flush=True)
    print('DONE', flush=True)
