"""B-543: reverse attribute query ('X มี อะไรบ้าง'). LEDGER pre-reg 2026-10-25.
S1: in-session teach/retract/seed/unknown + save. S2: fresh-process round-trip.
S3: noninterference (corpus battery + seeded skills)."""
import json, random, subprocess, sys, os
sys.path.insert(0, os.getcwd())
from hsml import HSML
import b521, b526
from b527 import SKILLS
from cur7 import gen as cgen

PATH = 'logs/b543_mem.pkl'

def q(h, s):
    return h.hear(s)

def s1():
    h = HSML(seed=0); out = {}
    for s in b521.gen_corpus(random.Random(0), 8):
        h.hear(s)
    # C4a: unknown name -> abstain
    out['c4_unknown'] = q(h, 'เหยี่ยว มี อะไรบ้าง')['kind']
    # C1: teach a new name two attrs -> query lists both
    q(h, 'เหยี่ยว มี หงอน'); q(h, 'เหยี่ยว มี กรงเล็บ')
    r = q(h, 'เหยี่ยว มี อะไรบ้าง'); out['c1_query'] = (r['kind'], sorted(r.get('attrs', [])))
    # 'อะไรบ้าง' must NOT have been stored as an attr anywhere
    out['c1_no_pollution'] = 'อะไรบ้าง' not in h.mem.attrs.vocab()
    # C2: retract one -> query lists only the remaining one
    q(h, 'เหยี่ยว ไม่มี หงอน')
    r = q(h, 'เหยี่ยว มี อะไรบ้าง'); out['c2_after_retract'] = (r['kind'], r.get('attrs'))
    # C3: seed animal lists its corpus-taught attrs
    r = q(h, 'นก มี อะไรบ้าง'); out['c3_seed'] = (r['kind'], sorted(r.get('attrs', [])))
    # C4b: fully retracted name -> honest abstain (known name, empty row)
    q(h, 'เหยี่ยว ไม่มี กรงเล็บ')
    r = q(h, 'เหยี่ยว มี อะไรบ้าง'); out['c4_empty'] = (r['kind'], r.get('source'))
    # forward probes still agree with the reverse view (same store)
    q(h, 'วางนก มี ปีก') if False else None
    r = q(h, 'จะงอยปาก'); out['c3_forward'] = (r['kind'], r.get('text'))
    h.save(PATH)
    return out

def s2():
    h = HSML.load(PATH, seed=0); out = {}
    r = q(h, 'นก มี อะไรบ้าง'); out['c5_seed'] = (r['kind'], sorted(r.get('attrs', [])))
    r = q(h, 'เหยี่ยว มี อะไรบ้าง'); out['c5_empty'] = (r['kind'], r.get('source'))
    # teach AFTER load, then query (reverse view of post-load learning)
    q(h, 'วาฬ มี ครีบหลัง')
    r = q(h, 'วาฬ มี อะไรบ้าง'); out['c5_post_load'] = (r['kind'], r.get('attrs'))
    return out

def s3():
    h = HSML(seed=0); out = {}
    for s in b521.gen_corpus(random.Random(0), 8):
        h.hear(s)
    out['c6_battery'] = all(ok == n for ok, n in b526.battery(h.mem.attrs).values())
    seeded = {}
    for task in SKILLS:
        te = random.Random(1000); okc = n = 0
        for sc in (1, 2, 3, 4):
            for _ in range(10):
                x, y, rr = cgen(task, te, sc)
                a = h.mem.answer(f'{SKILLS[task]} ของ {x} คืออะไร')
                n += 1; okc += (a.get('kind') == 'skill_answer' and a.get('result') == rr)
        seeded[task] = f'{okc}/{n}'
    out['c6_seeded'] = seeded
    return out

def run():
    outs = {}
    for mode in ('s1', 's2', 's3'):
        cache = f'logs/b543_{mode}.json'
        if os.path.exists(cache):
            outs[mode] = json.load(open(cache))
        else:
            p = subprocess.run([sys.executable, '-u', 'b543.py', mode], capture_output=True, text=True)
            assert p.returncode == 0, (mode, p.stderr)
            outs[mode] = json.loads(p.stdout.strip().splitlines()[-1])
    a, b, c = outs['s1'], outs['s2'], outs['s3']
    checks = {
        'c1': a['c1_query'] == ['attr_list', ['กรงเล็บ', 'หงอน']] and a['c1_no_pollution'],
        'c2': a['c2_after_retract'] == ['attr_list', ['กรงเล็บ']],
        'c3': (a['c3_seed'][0] == 'attr_list'
               and set(a['c3_seed'][1]) == set(sorted(b521.ANIMALS['นก']))
               and a['c3_forward'][0] == 'attr_answer' and 'นก' in str(a['c3_forward'][1])),
        'c4': a['c4_unknown'] == 'abstain' and a['c4_empty'][0] == 'abstain' and a['c4_empty'][1] == 'attr_reverse_empty',
        'c5': (set(b['c5_seed'][1]) == set(sorted(b521.ANIMALS['นก']))
               and b['c5_empty'][0] == 'abstain'
               and b['c5_post_load'] == ['attr_list', ['ครีบหลัง']]),
        'c6': c['c6_battery'] and all(v == '40/40' for v in c['c6_seeded'].values()),
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
