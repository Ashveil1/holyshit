"""B-530: compositional dialog teaching - taught skills accumulate as LIB primitives.
Teach double then quad through the b529 dialog protocol; measure quad induction cost
WITH double in LIB vs ABLATED (double popped) - same pairs/seeds/cap, so the tried
delta credits the accumulated library. LEDGER pre-reg 2026-10-24."""
import random, json, sys
import cur7 as C
from cur7 import LIB, show_prog, make_fn
from b529 import teach, Teacher, NEW, CAP7, induce
from b527 import HSMLMemory, derive_skills, load_logged, SKILLS, SKILL_BY_WORD
from b521 import gen_corpus
from b526 import battery

NEW['quad'] = 'สี่เท่า'

def as_primitive(skill):
    """Wrap a taught skill's program as a callable LIB primitive (cur7 wrapping)."""
    f0 = make_fn(skill[0]); C.CAPF[0] = 20000
    return (lambda ff: (lambda a, b: ff(a, b)))(f0)

def teach_seq(with_double, seed=0):
    """Teach double then quad. Returns (mem, dlog, qlog)."""
    mem = HSMLMemory()
    mem.skills = derive_skills(load_logged())
    dok, dlog = teach(mem, Teacher(lambda x: 2 * x), 'double', seed=seed)
    print(f'  double taught={dok} {dlog}', flush=True)
    assert dok, 'double teaching failed - cannot run B-530'
    if with_double:
        LIB['double'] = as_primitive(mem.skills['double'])
    else:
        LIB.pop('double', None)
    qok, qlog = teach(mem, Teacher(lambda x: 4 * x), 'quad', seed=seed)
    print(f'  quad taught={qok} (with_double={with_double}) {qlog}', flush=True)
    return mem, dlog, qok, qlog

def accuracy(mem, word, truth, lo=40, hi=2000, n=40):
    te = random.Random(1000); ok = 0
    for _ in range(n):
        x = te.randrange(lo, hi)
        ans = mem.answer(f'{word} ของ {x} คืออะไร')
        ok += (ans.get('kind') == 'skill_answer' and ans.get('result') == truth(x))
    return f'{ok}/{n}'

def run_battery():
    out = {}
    # ---- main arm: double in LIB ----
    print('ARM with-double', flush=True)
    mem, dlog, qok, qlog = teach_seq(True)
    out['c1_double'] = dlog
    out['c1_quad'] = qlog
    if qok:
        out['c2_quad_accuracy'] = accuracy(mem, NEW['quad'], lambda x: 4 * x)
        out['quad_prog'] = mem.skills['quad'][2].get('prog') or show_prog(mem.skills['quad'][0])
        out['quad_calls_double'] = "'double'" in show_prog(mem.skills['quad'][0]) or 'double' in show_prog(mem.skills['quad'][0])
        print('C2', out['c2_quad_accuracy'], 'calls_double', out['quad_calls_double'], flush=True)
    # ---- C3 ablation arm: double popped from LIB ----
    print('ARM ablated', flush=True)
    mem2, _, qok2, qlog2 = teach_seq(False)
    out['c3_ablated_quad'] = {'ok': qok2, **qlog2}
    if qok and qlog.get('tried') and qlog2.get('tried'):
        out['c3_tried'] = {'with_double': qlog['tried'], 'ablated': qlog2['tried']}
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
    rng = random.Random(0)
    for s in gen_corpus(rng, 8):
        mem.attrs.observe(s.split())
    b = battery(mem.attrs)
    out['c4_seeded'] = c4
    out['c4_attr_battery'] = {k: f'{v[0]}/{v[1]}' for k, v in b.items()}
    print('C4', c4, flush=True)
    # ---- C5 garbage quad teacher (with-double LIB = stronger condition) ----
    mem3 = HSMLMemory(); mem3.skills = derive_skills(load_logged())
    dok3, _ = teach(mem3, Teacher(lambda x: 2 * x), 'double', seed=0)
    LIB['double'] = as_primitive(mem3.skills['double'])
    grng = random.Random(555); memo = {}
    def gtruth(x):
        if x not in memo: memo[x] = grng.randrange(0, 1000)
        return memo[x]
    gok, glog = teach(mem3, Teacher(gtruth), 'quad', seed=0)
    out['c5_garbage_quad'] = {'stored': gok, **glog}
    print('C5', gok, glog, flush=True)
    return out

if __name__ == '__main__':
    out = run_battery()
    c1 = out['c1_quad'].get('pairs', 99) <= 20 and out['c1_double'].get('pairs', 99) <= 20
    acc = out.get('c2_quad_accuracy', '0/40').split('/')[0]
    c2 = acc.isdigit() and int(acc) >= 38
    t = out.get('c3_tried')
    c3 = bool(t) and (t['with_double'] * 2 <= t['ablated'] or not out['c3_ablated_quad']['ok'])
    c4 = all(v == '160/160' for k, v in out['c4_seeded'].items() if k != 'double') and out['c4_seeded']['double'] == '40/40'
    c5 = not out['c5_garbage_quad']['stored']
    verdict = 'PASS' if (c1 and c2 and c3 and c4 and c5) else 'FAIL'
    print(json.dumps({'verdict': verdict, 'c1': c1, 'c2': c2, 'c3': c3, 'c4': c4, 'c5': c5, **out},
                     ensure_ascii=False), flush=True)
    print('DONE', flush=True)
