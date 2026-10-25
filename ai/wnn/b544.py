"""B-544: storage safety - questions are not facts + three-way yes/no questions.
LEDGER pre-reg 2026-10-25 (parent greenlight after eval_ash3 baseline).
S1: guards + nonmutation + ordinary learning + yes/no three-way + save.
S2: fresh-process round-trip of negative evidence + re-teach clearing.
S3: noninterference (corpus battery + seeded skills)."""
import json, random, subprocess, sys, os
sys.path.insert(0, os.getcwd())
from hsml import HSML
import b521, b526
from b527 import SKILLS
from cur7 import gen as cgen

PATH = 'logs/b544_mem.pkl'

def q(h, s):
    return h.hear(s)

def s1():
    h = HSML(seed=0); out = {}
    for s in b521.gen_corpus(random.Random(0), 8):
        h.hear(s)
    # C1: the baseline defect itself - question phrase must NOT be stored now
    r = q(h, 'นก มี กี่ลักษณะ'); out['c1_reject'] = (r['kind'], r.get('text'))
    r = q(h, 'กี่ลักษณะ'); out['c1_probe'] = (r['kind'], r.get('text'))
    r = q(h, 'นก มี อะไรบ้าง'); out['c1_reverse'] = (r['kind'], sorted(r.get('attrs', [])))
    # C2: question word in NAME position
    r = q(h, 'อะไร มี ปีก'); out['c2_reject'] = (r['kind'], r.get('text'))
    r = q(h, 'ปีก'); out['c2_probe'] = (r['kind'], r.get('text'))  # must not contain 'อะไร'
    # C3: particle in attr position
    r = q(h, 'หมา มี ครับ'); out['c3_reject'] = (r['kind'], r.get('text'))
    r = q(h, 'ครับ'); out['c3_probe'] = (r['kind'],)
    # C4: ordinary new-attribute learning unaffected
    r = q(h, 'ชินชิลล่า มี ขนนุ่ม'); out['c4_learn'] = r['kind']
    r = q(h, 'ขนนุ่ม'); out['c4_probe'] = (r['kind'], r.get('text'))
    # C5: yes/no three-way
    r = q(h, 'นก มี ปีก ไหม'); out['c5_taught'] = (r['kind'], r.get('text'), r.get('answer'))
    r = q(h, 'นก มี เกล็ด ไหม'); out['c5_never'] = (r['kind'], r.get('text'), r.get('answer'))
    q(h, 'ชินชิลล่า ไม่มี ขนนุ่ม')
    r = q(h, 'ชินชิลล่า มี ขนนุ่ม ไหม'); out['c5_retracted'] = (r['kind'], r.get('text'), r.get('answer'))
    # guard inside yes/no frame
    r = q(h, 'อะไร มี ปีก ไหม'); out['c5_guard'] = r['kind']
    h.save(PATH)
    return out

def s2():
    h = HSML.load(PATH, seed=0); out = {}
    # C6: negative evidence survives load
    r = q(h, 'ชินชิลล่า มี ขนนุ่ม ไหม'); out['c6_loaded_neg'] = (r['kind'], r.get('text'), r.get('answer'))
    # re-teach clears the negative marker
    q(h, 'ชินชิลล่า มี ขนนุ่ม')
    r = q(h, 'ชินชิลล่า มี ขนนุ่ม ไหม'); out['c6_reteach'] = (r['kind'], r.get('text'), r.get('answer'))
    r = q(h, 'ขนนุ่ม'); out['c6_probe'] = (r['kind'], r.get('text'))
    return out

def s3():
    h = HSML(seed=0); out = {}
    for s in b521.gen_corpus(random.Random(0), 8):
        h.hear(s)
    out['c7_battery'] = all(ok == n for ok, n in b526.battery(h.mem.attrs).values())
    seeded = {}
    for task in SKILLS:
        te = random.Random(1000); okc = n = 0
        for sc in (1, 2, 3, 4):
            for _ in range(10):
                x, y, rr = cgen(task, te, sc)
                a = h.mem.answer(f'{SKILLS[task]} ของ {x} คืออะไร')
                n += 1; okc += (a.get('kind') == 'skill_answer' and a.get('result') == rr)
        seeded[task] = f'{okc}/{n}'
    out['c7_seeded'] = seeded
    return out

def run():
    outs = {}
    for mode in ('s1', 's2', 's3'):
        cache = f'logs/b544_{mode}.json'
        if os.path.exists(cache):
            outs[mode] = json.load(open(cache))
        else:
            p = subprocess.run([sys.executable, '-u', 'b544.py', mode], capture_output=True, text=True)
            assert p.returncode == 0, (mode, p.stderr)
            outs[mode] = json.loads(p.stdout.strip().splitlines()[-1])
    a, b, c = outs['s1'], outs['s2'], outs['s3']
    checks = {
        'c1': (a['c1_reject'][0] == 'unsupported_question' and a['c1_probe'][0] == 'abstain'
               and a['c1_reverse'][0] == 'attr_list' and 'กี่ลักษณะ' not in a['c1_reverse'][1]),
        'c2': a['c2_reject'][0] == 'unsupported_question' and 'อะไร' not in str(a['c2_probe'][1]),
        'c3': a['c3_reject'][0] == 'unsupported_question' and a['c3_probe'][0] == 'abstain',
        'c4': a['c4_learn'] == 'observed' and a['c4_probe'][0] == 'attr_answer' and 'ชินชิลล่า' in str(a['c4_probe'][1]),
        'c5': (a['c5_taught'] == ['yesno', 'ใช่', 'yes']
               and a['c5_never'] == ['yesno', 'ไม่รู้', 'unknown']
               and a['c5_retracted'] == ['yesno', 'ไม่', 'no_explicit']
               and a['c5_guard'] == 'abstain'),
        'c6': (b['c6_loaded_neg'] == ['yesno', 'ไม่', 'no_explicit']
               and b['c6_reteach'] == ['yesno', 'ใช่', 'yes']
               and b['c6_probe'][0] == 'attr_answer' and 'ชินชิลล่า' in str(b['c6_probe'][1])),
        'c7': c['c7_battery'] and all(v == '40/40' for v in c['c7_seeded'].values()),
    }
    out = {**outs, **checks}
    out['verdict'] = 'PASS' if all(checks.values()) else 'FAIL'
    print(json.dumps(out, ensure_ascii=False))
    print('DONE')

if __name__ == '__main__':
    modes = {'s1': s1, 's2': s2, 's3': s3}
    if len(sys.argv) > 1 and sys.argv[1] in modes:
        print(json.dumps(modes[sys.argv[1]](), ensure_ascii=False))
    else:
        run()
