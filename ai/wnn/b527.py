"""B-527 (Link C): program-skill memory -> dialog answer path.
One memory object serves BOTH the B-521/B-523 attribute battery (CountBackend + decide)
AND a skill store of cur7-induced programs; queries arrive as Thai sentences and are
answered by executing stored programs or by the attribute lookup - real data flow.
Skills are seeded from b515's oops legs: re-derived deterministically (same seed/config)
and verified show_prog == logged string in logs/b515_oops.log before use (provenance).
LEDGER pre-reg 2026-10-24. Number parse/format and sentence frames are DESIGNED (named)."""
import random, json, sys, re
from collections import defaultdict
from itertools import combinations
from b521 import ANIMALS, ATTRS, gen_corpus
from b526 import CountBackend, decide
import cur7 as C
from cur7 import gen as cgen, show_prog, make_fn
from b515 import setup, capture_lists, search_oops, CAP

SKILLS = {'even': 'เลขคู่', 'sumto': 'ผลบวกถึง', 'square': 'กำลังสอง', 'choose2': 'จับคู่สอง'}
SKILL_BY_WORD = {v: k for k, v in SKILLS.items()}

class HSMLMemory:
    """One memory: attribute tables + skill store, one dialog front."""
    def __init__(self):
        self.attrs = CountBackend()
        self.skills = {}   # task -> (prog_tuple, fn, provenance)
    def answer(self, sentence):
        toks = sentence.split()
        # skill query frame (DESIGNED): "<skillword> ของ <n> คืออะไร"
        m = re.fullmatch(r'(\S+) ของ (\d+) คืออะไร', sentence)
        if m and m.group(1) in SKILL_BY_WORD:
            task = SKILL_BY_WORD[m.group(1)]
            x = int(m.group(2))
            if task not in self.skills:
                return {'kind': 'no_skill', 'skill': task}
            _, fn, prov = self.skills[task]
            try:
                r = fn(x, 1)
            except Exception:
                return {'kind': 'skill_failed', 'skill': task}
            return {'kind': 'skill_answer', 'skill': task, 'x': x, 'result': r,
                    'sentence': f'{m.group(1)} ของ {x} คือ {r}', 'provenance': prov}
        # attribute probe path (B-523 semantics)
        probe = [t for t in toks if t in ATTRS or t == 'เขา']
        kind, pl = decide(self.attrs, probe)
        return {'kind': kind, **pl}

def derive_skills(logged):
    """Re-derive b515 oops programs deterministically; verify against the log strings."""
    store = {}
    for task in ('even', 'sumto', 'square', 'choose2'):
        train = setup(task, seed=0)
        L = capture_lists(train)
        p, tried, dt = search_oops(train, L, lambda ph: 256 * 2 ** ph)
        assert p is not None, f'{task}: re-derivation failed'
        s = show_prog(p)
        assert s == logged[task], f'{task}: re-derived program != b515 logged program'
        C.CAPF[0] = 20000
        store[task] = (p, make_fn(p), {'source': 'b515_oops', 'tried': tried})
    return store

def load_logged():
    logged = {}
    for path in ('logs/b515_oops.log', 'logs/b515_progs.log'):
        for line in open(path):
            line = line.strip()
            if not line.startswith('{'):
                continue
            d = json.loads(line)
            if d.get('mode') == 'oops' and d.get('prog'):
                logged[d['task']] = d['prog']  # progs.log (followup) wins; oops.log even leg has no prog field
    return logged

def run_battery():
    out = {}
    mem = HSMLMemory()
    mem.skills = derive_skills(load_logged())
    # ---- C1: execution accuracy through the sentence path (b515 unseen protocol) ----
    c1 = {}
    for task in SKILLS:
        te = random.Random(1000)
        ok = n = 0
        for sc in (1, 2, 3, 4):
            for _ in range(40):
                x, y, r = cgen(task, te, sc)
                ans = mem.answer(f'{SKILLS[task]} ของ {x} คืออะไร')
                n += 1
                ok += (ans.get('kind') == 'skill_answer' and ans.get('result') == r)
        c1[task] = f'{ok}/{n}'
    out['c1_skill_sentence_accuracy'] = c1
    # ---- C2: copier baseline on the same unseen inputs (verbatim train pairs only) ----
    cop = {}
    for task in SKILLS:
        train = setup(task, seed=0)
        seen = {x: r for x, y, r in train}
        te = random.Random(1000)
        ok = n = 0
        for sc in (1, 2, 3, 4):
            for _ in range(40):
                x, y, r = cgen(task, te, sc)
                n += 1
                ok += (x in seen and seen[x] == r)
        cop[task] = f'{ok}/{n}'
    out['c2_copier_unseen'] = cop
    # ---- C3: no-skill abstain ----
    a = mem.answer('ตัวหารร่วมมาก ของ 12 คืออะไร')
    out['c3_no_skill_query'] = a
    # ---- C4: attribute battery with skills loaded ----
    rng = random.Random(0)
    for s in gen_corpus(rng, 8):
        mem.attrs.observe(s.split())
    from b526 import battery
    b = battery(mem.attrs)
    out['c4_attr_battery'] = {k: f'{v[0]}/{v[1]}' for k, v in b.items()}
    # ---- C5: garbage control - induction on shuffled pairs finds nothing ----
    task = 'sumto'
    train = setup(task, seed=0)
    rng5 = random.Random(555)
    sh = [(x, y, rng5.randrange(0, 1000)) for x, y, r in train]
    L = capture_lists(train)
    p5, tried5, _ = search_oops(sh, L, lambda ph: 256 * 2 ** ph, cap=611365)
    out['c5_shuffled_induction'] = {'found': p5 is not None, 'tried': tried5}
    return out

if __name__ == '__main__':
    print(json.dumps(run_battery(), ensure_ascii=False), flush=True)
    print('DONE', flush=True)
