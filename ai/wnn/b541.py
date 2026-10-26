"""B-541: no acknowledgement without persisted learning - dynamic name/attr vocabulary
vs honest rejection. LEDGER pre-reg 2026-10-25 (review-directed after eval_ash baseline).
S1: dynamic learning + rejection + invariant + save. S2: fresh-process round-trip.
C5: separate fresh memory noninterference (standard corpus battery + seeded skills)."""
import json, random, re, subprocess, sys, os
sys.path.insert(0, os.getcwd())
from hsml import HSML
import b521, b526
from b527 import SKILLS
from cur7 import gen as cgen

PATH = 'logs/b541_mem.pkl'

def q(h, s):
    return h.hear(s)

def s1():
    h = HSML(seed=0); out = {}
    # C3a: rejections BEFORE any learning
    out['c3_sawasdee'] = q(h, 'สวัสดี')['kind']
    out['c3_unspaced'] = q(h, 'เลขคู่ของ7คืออะไร')['kind']
    out['c3_unknown_probe'] = q(h, 'เขา')['kind']
    out['c3_unobserved_attr'] = q(h, 'เกล็ด')['kind']           # known attr, never observed
    out['c3_attr_no_frame'] = q(h, 'นก บิน ปีก')['kind']        # attr content, no designed frame
    # C1: new-name learning, acknowledged AND persisted
    out['c1_ack'] = q(h, 'เหยี่ยว มี ปีก')['kind']
    r = q(h, 'ปีก'); out['c1_probe_kind'] = r['kind']; out['c1_probe_text'] = r.get('text')
    out['c1_multi_frame'] = q(h, 'ดู เกล็ด ของ ปลาใหม่')['kind']
    r = q(h, 'เกล็ด'); out['c1_probe2'] = (r['kind'], r.get('text'))
    # C2: new-attr learning grounded by frame position
    out['c2_ack'] = q(h, 'ส้ม มี เปรี้ยว')['kind']
    r = q(h, 'เปรี้ยว'); out['c2_probe'] = (r['kind'], r.get('text'), r.get('decision'))
    # C6: no-ack-without-store invariant over a batch (new names x new+known attrs)
    batch = [('ควาย มี หาง', 'หาง', 'ควาย'), ('ควาย มี ขา', 'ขา', 'ควาย'),
             ('นกกระจอก มี ปีก', 'ปีก', 'นกกระจอก'), ('มะม่วง มี หวาน', 'หวาน', 'มะม่วง'),
             ('กระดาษ มี บาง', 'บาง', 'กระดาษ')]
    inv = []
    for s, a, n in batch:
        r1 = q(h, s)
        r2 = q(h, a)
        ok = (r1['kind'] == 'observed' and r2['kind'] == 'attr_answer' and n in str(r2.get('text')))
        inv.append(ok)
    out['c6_invariant'] = inv
    h.save(PATH)
    return out

def s2():
    h = HSML.load(PATH, seed=0); out = {}
    r = q(h, 'ปีก'); out['c4_wings'] = (r['kind'], r.get('text'))
    r = q(h, 'เปรี้ยว'); out['c4_sour'] = (r['kind'], r.get('text'))
    r = q(h, 'เลขคู่ ของ 8 คืออะไร'); out['c4_seeded'] = (r['kind'], r.get('result'))
    return out

def s3():
    # C5 noninterference: separate fresh memory + standard corpus only
    h = HSML(seed=0); out = {}
    for s in b521.gen_corpus(random.Random(0), 8):
        h.hear(s)
    out['c5_battery'] = all(ok == n for ok, n in b526.battery(h.mem.attrs).values())
    seeded = {}
    for task in SKILLS:
        te = random.Random(1000); okc = n = 0
        for sc in (1, 2, 3, 4):
            for _ in range(10):
                x, y, rr = cgen(task, te, sc)
                a = h.mem.answer(f'{SKILLS[task]} ของ {x} คืออะไร')
                n += 1; okc += (a.get('kind') == 'skill_answer' and a.get('result') == rr)
        seeded[task] = f'{okc}/{n}'
    out['c5_seeded'] = seeded
    return out

def run():
    outs = {}
    for mode in ('s1', 's2', 's3'):
        cache = f'logs/b541_{mode}.json'
        if os.path.exists(cache):
            outs[mode] = json.load(open(cache))
        else:
            p = subprocess.run([sys.executable, '-u', 'b541.py', mode], capture_output=True, text=True)
            assert p.returncode == 0, (mode, p.stderr)
            outs[mode] = json.loads(p.stdout.strip().splitlines()[-1])
    a, b, c = outs['s1'], outs['s2'], outs['s3']
    checks = {
        'c1': (a['c1_ack'] == 'observed' and a['c1_probe_kind'] == 'attr_answer'
               and 'เหยี่ยว' in a['c1_probe_text'] and a['c1_multi_frame'] == 'observed'
               and a['c1_probe2'][0] == 'attr_answer' and 'ปลาใหม่' in a['c1_probe2'][1]),
        'c2': a['c2_ack'] == 'observed' and a['c2_probe'][0] == 'attr_answer' and a['c2_probe'][1] == 'ส้ม' and a['c2_probe'][2] == 'unique',
        'c3': (a['c3_sawasdee'] == 'abstain' and a['c3_unspaced'] == 'abstain'
               and a['c3_unknown_probe'] == 'abstain' and a['c3_unobserved_attr'] == 'abstain'
               and a['c3_attr_no_frame'] == 'abstain'),
        'c4': (b['c4_wings'][0] == 'attr_answer' and 'เหยี่ยว' in b['c4_wings'][1]
               and b['c4_sour'][0] == 'attr_answer' and b['c4_sour'][1] == 'ส้ม'
               and b['c4_seeded'] == ['skill_answer', 1]),
        'c5': c['c5_battery'] and all(v == '40/40' for v in c['c5_seeded'].values()),
        'c6': all(a['c6_invariant']),
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
