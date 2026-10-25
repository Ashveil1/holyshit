"""B-533: capture-budgeted curriculum accounting (LEDGER pre-reg + Amendment 1, 2026-10-25).
Does B-531's reuse advantage survive TOTAL-tried accounting? Fix under test: zero-eval
capture (tried_cap=-1 materializes the enumeration lists without evaluating the first
(comb,init) block). Old-protocol capture tried is EXACTLY len(conds)*len(bases)*len(steps_pair)
(source analysis: the only tried_cap check in cur7.search is per (comb,init) block).
Amendment 1: pop fact/square/choose2/dblfact after derive_skills to replicate B-531's LIB."""
import random, json
import cur7 as C
from cur7 import LIB, show_prog
import b529, b515
from b529 import teach, Teacher, NEW, CAP7
from b530 import as_primitive, accuracy
from b515 import ABL, search_oops
from b527 import HSMLMemory, derive_skills, load_logged, SKILLS
from b521 import gen_corpus
from b526 import battery

NEW.update({'hexdec': 'สิบหกเท่า'})
TARGET = ('hexdec', lambda x: 16 * x)
AMEND1_POP = ('fact', 'square', 'choose2', 'dblfact', 'sumto')  # sumto re-added by teach_primitives in the reuse arm (b531 parity)
CAPS = []  # per-capture record: (arm, computed_block_tried)

def capture_old(train):
    """b515.capture_lists (tried_cap=0) but returning tried as well."""
    C.LIST_CAPTURE = {}
    _, tried, _ = C.search(train, ABL, tried_cap=0)
    lists = dict(C.LIST_CAPTURE); C.LIST_CAPTURE = None
    return lists, tried

def capture_zero(train):
    """The fix under test: tried_cap=-1 -> materialize lists, evaluate nothing."""
    C.LIST_CAPTURE = {}
    _, tried, _ = C.search(train, ABL, tried_cap=-1)
    lists = dict(C.LIST_CAPTURE); C.LIST_CAPTURE = None
    assert tried == 0, f'zero-eval capture evaluated {tried} candidates'
    return lists, 0

def block_tried(L):
    return len(L['conds']) * len(L['bases']) * len(L['steps_pair'])

def fresh_mem():
    mem = HSMLMemory(); mem.skills = derive_skills(load_logged())
    for t0 in AMEND1_POP: LIB.pop(t0, None)  # Amendment 1
    return mem

def teach_primitives(mem, seed=0):
    dok, _ = teach(mem, Teacher(lambda x: 2 * x), 'double', seed=seed)
    assert dok, 'double teaching failed'
    qok, _ = teach(mem, Teacher(lambda x: 4 * x), 'quad', seed=seed)
    assert qok, 'quad teaching failed'
    LIB['double'] = as_primitive(mem.skills['double'])
    LIB['quad'] = as_primitive(mem.skills['quad'])
    LIB['sumto'] = as_primitive(mem.skills['sumto'])

def arm_capture_compare(train, arm):
    Lo, to = capture_old(train)
    Lz, tz = capture_zero(train)
    CAPS.append((arm, block_tried(Lo)))
    return Lo, to, Lz, tz

def capture_zero_lists(train):
    return capture_zero(train)[0]

def run():
    out = {}
    key, truth = TARGET
    # ---- induce-equivalent train set (b529.induce builds it from teacher pairs) ----
    # We call teach() itself with b529.capture_lists patched per phase, so the teaching
    # dialog is byte-identical to b531; only the capture variant differs.
    orig_capture = b529.capture_lists
    # ---- ablated arm: zero-eval capture ----
    mem = fresh_mem()
    for p0 in ('double', 'quad', 'sumto'): LIB.pop(p0, None)
    b529.capture_lists = capture_zero_lists
    aok, alog = teach(mem, Teacher(truth), key)
    out['ablated'] = {'ok': aok, **alog}
    print('ablated zero-eval:', aok, alog, flush=True)
    # ---- reuse arm: zero-eval capture ----
    mem2 = fresh_mem()
    teach_primitives(mem2)
    rok, rlog = teach(mem2, Teacher(truth), key)
    out['reuse'] = {'ok': rok, **rlog}
    print('reuse zero-eval:', rok, rlog, flush=True)
    if rok:
        out['c2_accuracy'] = accuracy(mem2, NEW[key], truth)
        sp = show_prog(mem2.skills[key][0])
        out['target_prog'] = sp
        out['calls_primitive'] = [p for p in ('double', 'quad', 'sumto') if f"'{p}'" in sp]
    b529.capture_lists = orig_capture
    # ---- C1/C3: old vs zero capture list equality + exact old-capture tried (both arms) ----
    # Rebuild the exact train set teach() used: pairs from the same seed path is inside teach;
    # instead compare captures on the FIRST-round pairs, rebuilt identically (rng sample order).
    rng = random.Random(0); auxrng = random.Random(99)
    xs = rng.sample(range(1, 40), 5)
    pairs = [(x, truth(x)) for x in xs]
    train = [(x, auxrng.randrange(1, 50), y) for x, y in pairs]
    # ablated LIB state
    for p0 in ('double', 'quad', 'sumto'): LIB.pop(p0, None)
    C.EXCL.clear(); C.VALID[:] = []; C.ADV[:] = []
    for t0 in ('mod', 'mul', 'div', 'power', 'gcd', 'max', 'min'): LIB.pop(t0, None)
    C.search._baselib_done = False
    Lo_a, to_a = capture_old(train)
    C.search._baselib_done = False
    Lz_a, tz_a = capture_zero(train)
    out['c1_ablated_lists_equal'] = (Lo_a == Lz_a)
    out['c3_ablated_oldcapture_tried_measured'] = to_a
    out['c3_ablated_oldcapture_tried_computed'] = block_tried(Lo_a)
    # reuse LIB state (pinned 7 + double/quad/sumto)
    LIB['double'] = as_primitive(mem2.skills['double'])
    LIB['quad'] = as_primitive(mem2.skills['quad'])
    LIB['sumto'] = as_primitive(mem2.skills['sumto'])
    C.search._baselib_done = False
    Lo_r, to_r = capture_old(train)
    C.search._baselib_done = False
    Lz_r, tz_r = capture_zero(train)
    out['c1_reuse_lists_equal'] = (Lo_r == Lz_r)
    out['c3_reuse_oldcapture_tried_computed'] = block_tried(Lo_r)
    out['c3_reuse_oldcapture_tried_measured'] = to_r
    print('C1/C3:', {k: v for k, v in out.items() if k.startswith(('c1', 'c3'))}, flush=True)
    # ---- C4: total accounting both ways ----
    at = out['ablated'].get('tried') or 0
    rt = out['reuse'].get('tried') or 0
    out['c4'] = {
        'ablated_search_tried': at, 'reuse_search_tried': rt,
        'ablated_capture_tried_oldprotocol': out['c3_ablated_oldcapture_tried_computed'],
        'reuse_capture_tried_oldprotocol': out['c3_reuse_oldcapture_tried_computed'],
        'ablated_total_oldprotocol': at + out['c3_ablated_oldcapture_tried_computed'],
        'reuse_total_oldprotocol': rt + out['c3_reuse_oldcapture_tried_computed'],
        'ablated_total_zerocapture': at, 'reuse_total_zerocapture': rt,
    }
    # ---- C5 no interference (reuse mem) ----
    from cur7 import gen as cgen
    c5 = {}
    for task in SKILLS:
        te = random.Random(1000); okc = n = 0
        for sc in (1, 2, 3, 4):
            for _ in range(40):
                x, y, r = cgen(task, te, sc)
                ans = mem2.answer(f'{SKILLS[task]} ของ {x} คืออะไร')
                n += 1; okc += (ans.get('kind') == 'skill_answer' and ans.get('result') == r)
        c5[task] = f'{okc}/{n}'
    c5['double'] = accuracy(mem2, NEW['double'], lambda x: 2 * x)
    c5['quad'] = accuracy(mem2, NEW['quad'], lambda x: 4 * x)
    out['c5_seeded'] = c5
    print('C5:', c5, flush=True)
    # ---- verdict ----
    c1 = out['c1_ablated_lists_equal'] and out['c1_reuse_lists_equal']
    c2 = (not out['ablated']['ok'] and at == 700_001 and out['reuse']['ok']
          and rt == 29_478 and out['calls_primitive'] == ['quad'])
    c3 = (out['c3_ablated_oldcapture_tried_measured'] == out['c3_ablated_oldcapture_tried_computed']
          and out['c3_reuse_oldcapture_tried_measured'] == out['c3_reuse_oldcapture_tried_computed'])
    c5ok = all(v in ('160/160', '40/40') for v in c5.values())
    verdict = 'PASS' if (c1 and c2 and c3 and c5ok) else 'FAIL'
    print(json.dumps({'verdict': verdict, 'c1': c1, 'c2': c2, 'c3': c3, 'c5': c5ok, **out},
                     ensure_ascii=False), flush=True)
    print('DONE', flush=True)

if __name__ == '__main__':
    run()
