"""B-542: attribute retraction via designed negation frame 'X ไม่มี Y'.
LEDGER pre-reg 2026-10-25. S1: teach/retract/probe in-session + save. S2: fresh-process
round-trip of retracted state. S3: noninterference (corpus battery + seeded skills)."""
import json, random, subprocess, sys, os
sys.path.insert(0, os.getcwd())
from hsml import HSML
import b521, b526
from b527 import SKILLS
from cur7 import gen as cgen

PATH = 'logs/b542_mem.pkl'

def q(h, s):
    return h.hear(s)

def s1():
    h = HSML(seed=0); out = {}
    for s in b521.gen_corpus(random.Random(0), 8):   # seed world populated as in real use
        h.hear(s)
    # C5: retracting never-taught pairs -> honest nothing_to_retract, no state change
    out['c5_new_name'] = q(h, 'เหยี่ยว ไม่มี ปีก')['kind']          # name unknown entirely
    out['c5_seed_pair'] = q(h, 'นก ไม่มี เกล็ด')['kind']           # นก has no เกล็ด
    r = q(h, 'จะงอยปาก'); out['c5_state_unchanged'] = (r['kind'], r.get('text'))
    # setup: teach a NEW name a NEW attr + a second attr
    q(h, 'เหยี่ยว มี หงอน'); q(h, 'เหยี่ยว มี กรงเล็บ')
    r = q(h, 'หงอน'); out['setup_comb'] = (r['kind'], r.get('text'))
    # C1: retract -> probe no longer returns the name (attr unique to the new name)
    r = q(h, 'เหยี่ยว ไม่มี หงอน'); out['c1_retract'] = (r['kind'], r.get('retracted'), r.get('not_found'))
    r = q(h, 'หงอน'); out['c1_probe_after'] = (r['kind'], r.get('text'))
    # C2: the name's other attr survives
    r = q(h, 'กรงเล็บ'); out['c2_other_attr'] = (r['kind'], r.get('text'))
    # C3: retraction on a seeded name; conjunctive probe must no longer name it
    r = q(h, 'นก ไม่มี ปีก'); out['c3_retract_seed'] = (r['kind'], r.get('retracted'))
    r = q(h, 'ปีก และ จะงอยปาก'); out['c3_probe_seed'] = (r['kind'], r.get('text'))
    # C6: re-teach after retract restores
    r = q(h, 'นก มี ปีก'); out['c6_reteach_ack'] = r['kind']
    r = q(h, 'ปีก และ จะงอยปาก'); out['c6_reteach_probe'] = (r['kind'], r.get('text'))
    # multi-attr negation frame (both attrs unique to the new name)
    q(h, 'แมวน้ำ มี หนวด และ หางพัด')
    r = q(h, 'แมวน้ำ ไม่มี หนวด และ หางพัด'); out['c1_multi_neg'] = (r['kind'], r.get('retracted'))
    r = q(h, 'หางพัด'); out['c1_multi_probe'] = (r['kind'], r.get('text'))
    # partial retraction honesty: one real + one never-taught-for-this-name
    q(h, 'หมาป่า มี เขี้ยว')
    r = q(h, 'หมาป่า ไม่มี เขี้ยว และ เกล็ด'); out['c5_partial'] = (r['kind'], r.get('retracted'), r.get('not_found'))
    h.save(PATH)
    return out

def s2():
    h = HSML.load(PATH, seed=0); out = {}
    r = q(h, 'หงอน'); out['c4_comb_gone'] = (r['kind'], r.get('text'))
    r = q(h, 'กรงเล็บ'); out['c4_claws_kept'] = (r['kind'], r.get('text'))
    r = q(h, 'หางพัด'); out['c4_fins_gone'] = (r['kind'], r.get('text'))
    r = q(h, 'เขี้ยว'); out['c4_fangs_gone'] = (r['kind'], r.get('text'))
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
        cache = f'logs/b542_{mode}.json'
        if os.path.exists(cache):
            outs[mode] = json.load(open(cache))
        else:
            p = subprocess.run([sys.executable, '-u', 'b542.py', mode], capture_output=True, text=True)
            assert p.returncode == 0, (mode, p.stderr)
            outs[mode] = json.loads(p.stdout.strip().splitlines()[-1])
    a, b, c = outs['s1'], outs['s2'], outs['s3']
    checks = {
        'c1': (a['setup_comb'][0] == 'attr_answer' and 'เหยี่ยว' in str(a['setup_comb'][1])
               and a['c1_retract'][0] == 'retracted' and a['c1_retract'][1] == ['หงอน']
               and not a['c1_retract'][2]
               and a['c1_probe_after'][0] == 'abstain'
               and a['c1_multi_neg'][0] == 'retracted' and sorted(a['c1_multi_neg'][1]) == ['หนวด', 'หางพัด']
               and a['c1_multi_probe'][0] == 'abstain'),
        'c2': a['c2_other_attr'][0] == 'attr_answer' and 'เหยี่ยว' in str(a['c2_other_attr'][1]),
        'c3': (a['c3_retract_seed'][0] == 'retracted' and a['c3_retract_seed'][1] == ['ปีก']
               and (a['c3_probe_seed'][0] == 'abstain' or 'นก' not in str(a['c3_probe_seed'][1]))),
        'c4': (b['c4_comb_gone'][0] == 'abstain' and b['c4_claws_kept'][0] == 'attr_answer'
               and 'เหยี่ยว' in str(b['c4_claws_kept'][1])
               and b['c4_fins_gone'][0] == 'abstain' and b['c4_fangs_gone'][0] == 'abstain'),
        'c5': (a['c5_new_name'] == 'nothing_to_retract' and a['c5_seed_pair'] == 'nothing_to_retract'
               and a['c5_state_unchanged'][0] == 'attr_answer' and 'นก' in str(a['c5_state_unchanged'][1])
               and a['c5_partial'][0] == 'retracted' and a['c5_partial'][1] == ['เขี้ยว']
               and a['c5_partial'][2] == ['เกล็ด']),
        'c6': a['c6_reteach_ack'] == 'observed' and a['c6_reteach_probe'][0] == 'attr_answer' and 'นก' in str(a['c6_reteach_probe'][1]),
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
