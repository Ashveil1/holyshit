"""B-529 (Link D): in-dialog procedure teaching - a NEW skill enters the b527 skill
store through conversation only. Teacher emits/consumes SENTENCES; its truth function
only renders sentence text, the system side never touches it. Frames + number parsing
are DESIGNED (named): naming ('วิธีนี้ชื่อ <word>'), example ('ถ้า n เป็น <x> ตอบ <y>'),
confirmation reply ('ตอบ <y>'). Induction = cur7/OOPS on parsed pairs with NO VALID/ADV
extra supervision (honest: only teacher pairs). Confirmation on held-out inputs gates
storage. LEDGER pre-reg 2026-10-24."""
import random, json, re, sys
import cur7 as C
from cur7 import search, show_prog, make_fn, LIB, VALID, ADV, EXCL
from b515 import ABL, capture_lists, search_oops
from b527 import HSMLMemory, derive_skills, load_logged, SKILLS, SKILL_BY_WORD
from b521 import gen_corpus
from b526 import battery

EX_RE = re.compile(r'ถ้า n เป็น (\d+) ตอบ (\d+)')
NAME_RE = re.compile(r'วิธีนี้ชื่อ (\S+)')
CONF_RE = re.compile(r'ตอบ (\d+)')
CAP7 = 700_000
NEW = {'double': 'สองเท่า'}

class Teacher:
    """Scripted teacher. truth() only renders sentence text."""
    def __init__(self, truth):
        self.truth = truth
    def name_sentence(self, word): return f'วิธีนี้ชื่อ {word}'
    def example_sentence(self, x): return f'ถ้า n เป็น {x} ตอบ {self.truth(x)}'
    def confirm_reply(self, x): return f'ตอบ {self.truth(x)}'

def induce(pairs, cap=CAP7):
    """cur7/OOPS on parsed pairs only; library pinned as b515.setup, no VALID/ADV."""
    aux = random.Random(99)
    train = [(x, aux.randrange(1, 50), y) for x, y in pairs]
    for t0 in ('mod', 'mul', 'div', 'power', 'gcd', 'max', 'min'): LIB.pop(t0, None)
    search._baselib_done = False
    EXCL.clear(); VALID[:] = []; ADV[:] = []
    L = capture_lists(train)
    p, tried, _ = search_oops(train, L, lambda ph: 256 * 2 ** ph, cap=cap)
    return p, tried

def teach(mem, teacher, skill_key, rounds=3, ex0=5, cap=CAP7, seed=0):
    """The teaching dialog, system side. Returns (ok, log)."""
    word = NAME_RE.fullmatch(teacher.name_sentence(NEW[skill_key])).group(1)
    rng = random.Random(seed)
    pairs = []
    for x in rng.sample(range(1, 40), ex0):
        m = EX_RE.fullmatch(teacher.example_sentence(x))
        pairs.append((int(m.group(1)), int(m.group(2))))
    tried_tot = 0; confs = 0
    for rnd in range(1, rounds + 1):
        print(f'  teach round {rnd}: inducing on {len(pairs)} pairs...', flush=True)
        p, tried = induce(pairs, cap)
        tried_tot += tried
        print(f'  teach round {rnd}: tried={tried} found={p is not None}', flush=True)
        if p is None:
            return False, {'fail': 'induction exhausted', 'round': rnd, 'tried': tried_tot,
                           'pairs': len(pairs), 'confirmations': confs}
        fn = make_fn(p); C.CAPF[0] = 20000
        good = True
        for cx in rng.sample(range(40, 400), 3):
            ty = int(CONF_RE.fullmatch(teacher.confirm_reply(cx)).group(1))
            confs += 1
            try: ry = fn(cx, 1)
            except Exception: ry = None
            pairs.append((cx, ty))
            if ry != ty: good = False; break
        if good:
            SKILL_BY_WORD[word] = skill_key
            mem.skills[skill_key] = (p, fn, {'source': 'dialog', 'round': rnd,
                                             'tried': tried_tot, 'examples': len(pairs)})
            return True, {'round': rnd, 'tried': tried_tot, 'pairs': len(pairs),
                          'confirmations': confs, 'prog': show_prog(p)}
        if rnd < rounds:
            for x in rng.sample(range(1, 40), 2):
                m = EX_RE.fullmatch(teacher.example_sentence(x))
                pairs.append((int(m.group(1)), int(m.group(2))))
    return False, {'fail': 'confirmation cap', 'rounds': rounds, 'tried': tried_tot,
                   'pairs': len(pairs), 'confirmations': confs}

def run_battery():
    out = {}
    mem = HSMLMemory()
    mem.skills = derive_skills(load_logged())   # the 4 seeded skills (cache-verified)
    # ---- C1+C5: teach 'double' through dialog ----
    ok, log = teach(mem, Teacher(lambda x: 2 * x), 'double')
    out['c1_teaching'] = {'ok': ok, **log,
                          'supervision': (log['pairs'] + 0)}
    print('C1 done', ok, log, flush=True)
    # ---- C2: taught skill on 40 unseen inputs through the sentence path ----
    if ok:
        te = random.Random(1000); okc = n = 0; fails = []
        for _ in range(40):
            x = te.randrange(40, 2000)
            ans = mem.answer(f'สองเท่า ของ {x} คืออะไร')
            n += 1
            good = ans.get('kind') == 'skill_answer' and ans.get('result') == 2 * x
            okc += good
            if not good and len(fails) < 3: fails.append({'x': x, 'ans': ans})
        out['c2_taught_accuracy'] = f'{okc}/{n}'
        if fails: out['c2_fails'] = fails
        print('C2 done', out['c2_taught_accuracy'], flush=True)
    # ---- C3: no interference - seeded skills 160/160 + B-523 battery ----
    from cur7 import gen as cgen
    c3 = {}
    for task in SKILLS:
        te = random.Random(1000); okc = n = 0
        for sc in (1, 2, 3, 4):
            for _ in range(40):
                x, y, r = cgen(task, te, sc)
                ans = mem.answer(f'{SKILLS[task]} ของ {x} คืออะไร')
                n += 1
                okc += (ans.get('kind') == 'skill_answer' and ans.get('result') == r)
        c3[task] = f'{okc}/{n}'
    rng = random.Random(0)
    for s in gen_corpus(rng, 8):
        mem.attrs.observe(s.split())
    b = battery(mem.attrs)
    out['c3_seeded'] = c3
    out['c3_attr_battery'] = {k: f'{v[0]}/{v[1]}' for k, v in b.items()}
    print('C3 done', c3, flush=True)
    # ---- C4: garbage teacher ends with NO new skill ----
    mem2 = HSMLMemory(); mem2.skills = derive_skills(load_logged())
    grng = random.Random(555); memo = {}
    def gtruth(x):
        if x not in memo: memo[x] = grng.randrange(0, 1000)
        return memo[x]
    gok, glog = teach(mem2, Teacher(gtruth), 'double')
    out['c4_garbage_teacher'] = {'stored': gok, **glog, 'prog': glog.get('prog', None)}
    print('C4 done', gok, glog, flush=True)
    return out

if __name__ == '__main__':
    out = run_battery()
    c1 = out['c1_teaching']['ok'] and out['c1_teaching']['supervision'] <= 20
    acc = out.get('c2_taught_accuracy', '0/40').split('/')[0]
    c2 = acc.isdigit() and int(acc) >= 38
    c3 = all(v == '160/160' for v in out['c3_seeded'].values())
    c4 = not out['c4_garbage_teacher']['stored']
    verdict = 'PASS' if (c1 and c2 and c3 and c4) else 'FAIL'
    print(json.dumps({'verdict': verdict, 'c1': c1, 'c2': c2, 'c3': c3, 'c4': c4, **out},
                     ensure_ascii=False), flush=True)
    print('DONE', flush=True)
