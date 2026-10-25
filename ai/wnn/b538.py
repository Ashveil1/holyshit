"""B-538: conversational REVISION of a taught skill. LEDGER pre-reg 2026-10-25.
One conversation: teach double (2n), revise it through the same dialog path (3n),
failed-revision control (garbage teacher, full cap), seeded-word protection;
a fresh process then checks the revision persisted."""
import json, random, re, subprocess, sys
from hsml import HSML
from b527 import SKILLS
from cur7 import gen as cgen
import cur7 as C7

PATH = 'logs/b538_mem.pkl'
OLD = lambda x: 2 * x
NEW = lambda x: 3 * x

def teach_via_dialog(h, word, truth, seed=0, name=True):
    rng = random.Random(seed)
    if name:
        r = h.hear(f'วิธีนี้ชื่อ {word}')
        assert r['kind'] in ('naming', 'revision_opened'), r
    for x in rng.sample(range(1, 40), 5):
        r = h.hear(f'ถ้า n เป็น {x} ตอบ {truth(x)}')
    tries = 0
    while r['kind'] == 'confirmation_question':
        tries += 1
        assert tries < 50, 'confirmation loop'
        cx = int(re.fullmatch(r'ถ้า n เป็น (\d+) ตอบอะไร', r['text']).group(1))
        r = h.hear(f'ตอบ {truth(cx)}')
    return r

def probe(h, word, truth, n=10, seed=7):
    rng = random.Random(seed); ok = 0
    for _ in range(n):
        u = rng.randrange(400, 4000)
        r = h.hear(f'{word} ของ {u} คืออะไร')
        ok += (r['kind'] == 'skill_answer' and r.get('result') == truth(u))
    return f'{ok}/{n}'

def s1():
    h = HSML(seed=0)
    out = {}
    # C1: teach double, probe
    r = teach_via_dialog(h, 'สองเท่า', OLD)
    out['c1_stored'] = (r['kind'] == 'skill_stored'); out['c1_tried'] = r.get('tried')
    out['c1_probe'] = probe(h, 'สองเท่า', OLD)
    # C2: naming the same dialog-taught word opens a REVISION explicitly
    r = h.hear('วิธีนี้ชื่อ สองเท่า')
    out['c2_revision_opened'] = (r['kind'] == 'revision_opened')
    # C3: complete the revision to 3n; new behavior answers, old behavior gone
    r = teach_via_dialog(h, 'สองเท่า', NEW, seed=1, name=False)
    out['c3_revision_stored'] = (r['kind'] == 'skill_stored'); out['c3_tried'] = r.get('tried')
    out['c3_new_probe'] = probe(h, 'สองเท่า', NEW, seed=11)
    out['c3_old_gone'] = probe(h, 'สองเท่า', OLD, seed=11)  # distinguishing: 3u != 2u on all probe inputs
    # C4: revision provenance
    prov = h.mem.skills['สองเท่า'][2]
    out['c4_revision_count'] = prov.get('revision')
    out['c4_replaces_recorded'] = 'replaces' in prov
    # C5: failed-revision control - garbage teacher to full-cap exhaustion; revised skill intact
    r = h.hear('วิธีนี้ชื่อ สองเท่า')
    out['c5_revision_opened'] = (r['kind'] == 'revision_opened')
    grng = random.Random(555); memo = {}
    def gtruth(x):
        if x not in memo: memo[x] = grng.randrange(0, 1000)
        return memo[x]
    r = teach_via_dialog(h, 'สองเท่า', gtruth, seed=5, name=False)
    out['c5_final_kind'] = r['kind']; out['c5_tried'] = r.get('tried')
    out['c5_intact_probe'] = probe(h, 'สองเท่า', NEW, seed=12)
    # C6: induction LIB carries the corrected program
    out['c6_lib_has_word'] = 'สองเท่า' in C7.LIB
    if out['c6_lib_has_word']:
        C7.CAPF[0] = 20000
        out['c6_lib_executes_new'] = (C7.LIB['สองเท่า'](5, 1) == NEW(5))
    # C8: seeded-word protection (provenance)
    r = h.hear(f'วิธีนี้ชื่อ {SKILLS["even"]}')
    out['c8_reserved'] = (r['kind'] == 'abstain' and r.get('source') == 'reserved')
    te = random.Random(1000); okc = n = 0
    for sc in (1, 2, 3, 4):
        for _ in range(10):
            x, y, rr = cgen('even', te, sc)
            a = h.mem.answer(f'{SKILLS["even"]} ของ {x} คืออะไร')
            n += 1; okc += (a.get('kind') == 'skill_answer' and a.get('result') == rr)
    out['c8_even_probe'] = f'{okc}/{n}'
    h.save(PATH)
    return out

def s2():
    h = HSML.load(PATH, seed=0)
    out = {}
    out['c7_new_probe'] = probe(h, 'สองเท่า', NEW, seed=13)
    out['c7_old_gone'] = probe(h, 'สองเท่า', OLD, seed=13)
    prov = h.mem.skills['สองเท่า'][2]
    out['c7_revision_count'] = prov.get('revision')
    out['c7_replaces_recorded'] = 'replaces' in prov
    out['c7_lib_has_word'] = 'สองเท่า' in C7.LIB
    return out

def run():
    outs = {}
    for mode in ('s1', 's2'):
        p = subprocess.run([sys.executable, '-u', 'b538.py', mode], capture_output=True, text=True)
        assert p.returncode == 0, (mode, p.stderr)
        outs[mode] = json.loads(p.stdout.strip().splitlines()[-1])
    s1, s2 = outs['s1'], outs['s2']
    checks = {
        'c1': s1['c1_stored'] and s1['c1_probe'] == '10/10',
        'c2': s1['c2_revision_opened'],
        'c3': s1['c3_revision_stored'] and s1['c3_new_probe'] == '10/10' and s1['c3_old_gone'] == '0/10',
        'c4': s1['c4_revision_count'] == 1 and s1['c4_replaces_recorded'],
        'c5': s1['c5_final_kind'] == 'teach_failed' and s1['c5_intact_probe'] == '10/10',
        'c6': s1.get('c6_lib_has_word') and s1.get('c6_lib_executes_new'),
        'c7': s2['c7_new_probe'] == '10/10' and s2['c7_old_gone'] == '0/10' and s2['c7_revision_count'] == 1 and s2['c7_replaces_recorded'] and s2['c7_lib_has_word'],
        'c8': s1['c8_reserved'] and s1['c8_even_probe'] == '40/40',
    }
    out = {**outs, **checks}
    out['verdict'] = 'PASS' if all(checks.values()) else 'FAIL'
    print(json.dumps(out, ensure_ascii=False))
    print('DONE')

if __name__ == '__main__':
    modes = {'s1': s1, 's2': s2}
    if len(sys.argv) > 1 and sys.argv[1] in modes:
        print(json.dumps(modes[sys.argv[1]](), ensure_ascii=False))
    else:
        run()
