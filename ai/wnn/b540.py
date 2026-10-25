"""B-540: mixed-dialog end-to-end integration battery. LEDGER pre-reg 2026-10-25.
S1: ONE sustained mixed conversation - corpus observations, attr probes, teach double,
    teach quad WITH interleaved attr/skill utterances between examples, abandonment
    (ห้าเท่า partial -> switch to แปดเท่า), teach 16n, unknown abstains, revise quad
    4n->5n, stale checks, revalidate 16n (25n) + any other newly-stale taught skill,
    attr battery, log integrity, save (expectation table in extra).
S2: fresh process - load, all probes at recorded final behaviors, attr battery exact,
    abstains, teach สามเท่า 3n, bounded garbage control, log integrity."""
import json, os, pickle, random, re, subprocess, sys
from hsml import HSML
import b521, b526

PATH = 'logs/b540_mem.pkl'

def teach(h, word, truth, seed=0, name=True):
    rng = random.Random(seed)
    if name:
        r = h.hear(f'วิธีนี้ชื่อ {word}')
        assert r['kind'] in ('naming', 'revision_opened'), r
    else:
        r = {'kind': 'example'}
    for x in rng.sample(range(1, 40), 5):
        r = h.hear(f'ถ้า n เป็น {x} ตอบ {truth(x)}')
    tries = 0
    while r['kind'] == 'confirmation_question':
        tries += 1
        assert tries < 50, 'confirmation loop'
        cx = int(re.fullmatch(r'ถ้า n เป็น (\d+) ตอบอะไร', r['text']).group(1))
        r = h.hear(f'ตอบ {truth(cx)}')
    return r

def revalidate(h, word, truth):
    r = h.hear(f'วิธีนี้ชื่อ {word}')
    assert r['kind'] == 'revalidate_opened', r
    n = 0
    while r['kind'] in ('revalidate_opened', 'confirmation_question'):
        cx = int(re.fullmatch(r'ถ้า n เป็น (\d+) ตอบอะไร', r['text']).group(1))
        r = h.hear(f'ตอบ {truth(cx)}')
        n += 1
        assert n < 10
    return r

def probe(h, word, truth, n=10, seed=7):
    rng = random.Random(seed); ok = 0
    for _ in range(n):
        u = rng.randrange(400, 4000)
        r = h.hear(f'{word} ของ {u} คืออะไร')
        ok += (r['kind'] == 'skill_answer' and r.get('result') == truth(u))
    return f'{ok}/{n}'

def battery_ok(attrs):
    return all(ok == n for ok, n in b526.battery(attrs).values())

def s1():
    h = HSML(seed=0); out = {'tried': {}, 'chk': {}}
    # 1. corpus observations interleaved with everything below
    corpus = b521.gen_corpus(random.Random(0), 8)
    kinds = {h.hear(s)['kind'] for s in corpus}
    out['chk']['corpus_observed'] = sorted(kinds)
    # 2. attr probe
    r = h.hear('ปีก')
    out['chk']['attr_probe'] = (r['kind'], r.get('decision'))
    # 3. teach double clean
    r = teach(h, 'สองเท่า', lambda x: 2 * x, seed=0)
    out['double_stored'] = (r['kind'] == 'skill_stored'); out['tried']['double'] = r.get('tried')
    out['double_probe'] = probe(h, 'สองเท่า', lambda x: 2 * x)
    # 4. C1: teach quad WITH interleaves between examples
    rng = random.Random(1)
    r = h.hear('วิธีนี้ชื่อ สี่เท่า'); out['chk']['quad_naming'] = r['kind']
    xs = rng.sample(range(1, 40), 5)
    r = h.hear(f'ถ้า n เป็น {xs[0]} ตอบ {4 * xs[0]}')
    r = h.hear(f'ถ้า n เป็น {xs[1]} ตอบ {4 * xs[1]}')
    out['chk']['quad_ex2'] = r['kind']
    # interleave: attr observation, attr probe, double query - mid teaching context
    r = h.hear('ช้าง มี งา'); out['chk']['interleave_obs'] = r['kind']
    r = h.hear('งา'); out['chk']['interleave_attr'] = (r['kind'], r.get('decision'))
    r = h.hear('สองเท่า ของ 7 คืออะไร'); out['chk']['interleave_double'] = (r['kind'], r.get('result'))
    for x in xs[2:]:
        r = h.hear(f'ถ้า n เป็น {x} ตอบ {4 * x}')
    tries = 0
    while r['kind'] == 'confirmation_question':
        tries += 1; assert tries < 50
        cx = int(re.fullmatch(r'ถ้า n เป็น (\d+) ตอบอะไร', r['text']).group(1))
        r = h.hear(f'ตอบ {4 * cx}')
    out['quad_stored'] = (r['kind'] == 'skill_stored'); out['tried']['quad'] = r.get('tried')
    out['c1_quad_probe'] = probe(h, 'สี่เท่า', lambda x: 4 * x)
    # 5. C3: abandonment - partial ห้าเท่า discarded by switching name; complete แปดเท่า
    r = h.hear('วิธีนี้ชื่อ ห้าเท่า'); out['chk']['five_naming'] = r['kind']
    for x in random.Random(2).sample(range(1, 40), 2):
        r = h.hear(f'ถ้า n เป็น {x} ตอบ {5 * x}')
    out['chk']['five_partial'] = r['kind']
    r = teach(h, 'แปดเท่า', lambda x: 8 * x, seed=3)
    out['c3_eight_stored'] = (r['kind'] == 'skill_stored'); out['tried']['eight'] = r.get('tried')
    out['c3_eight_probe'] = probe(h, 'แปดเท่า', lambda x: 8 * x)
    r = h.hear('ห้าเท่า ของ 5 คืออะไร'); out['c3_five_abstain'] = r['kind']
    out['c3_eight_deps'] = h.mem.skills['แปดเท่า'][2].get('deps', [])
    # 6. teach 16n (LIB: double + quad - same regime as B-539 C1)
    r = teach(h, 'สิบหกเท่า', lambda x: 16 * x, seed=2)
    out['sixteen_stored'] = (r['kind'] == 'skill_stored'); out['tried']['sixteen'] = r.get('tried')
    out['c4_16_deps'] = h.mem.skills['สิบหกเท่า'][2].get('deps')
    out['sixteen_probe'] = probe(h, 'สิบหกเท่า', lambda x: 16 * x)
    # 7. C5: unknown abstains
    r = h.hear('ร้อยเท่า ของ 5 คืออะไร'); out['c5_unknown_skill'] = r['kind']
    r = h.hear('เขา'); out['c5_unknown_attr'] = r['kind']
    # 8. C4: revise quad 4n -> 5n inside the mixed dialog
    h.hear('วิธีนี้ชื่อ สี่เท่า')
    r = teach(h, 'สี่เท่า', lambda x: 5 * x, seed=6, name=False)
    out['c4_quad_revised'] = (r['kind'] == 'skill_stored'); out['tried']['quad_rev'] = r.get('tried')
    r = h.hear('สิบหกเท่า ของ 5 คืออะไร'); out['c4_16_response'] = r['kind']
    out['c4_double_unaffected'] = probe(h, 'สองเท่า', lambda x: 2 * x, seed=8)
    out['c4_quad_probe'] = probe(h, 'สี่เท่า', lambda x: 5 * x, seed=9)
    r = h.hear('ปีก'); out['c4_attr_after_revision'] = (r['kind'], r.get('decision'))
    # revalidate 16n to the recomposed 25n (teacher states it, as B-539)
    r = revalidate(h, 'สิบหกเท่า', lambda x: 25 * x)
    out['c4_reval_kind'] = r['kind']
    out['c4_16_probe'] = probe(h, 'สิบหกเท่า', lambda x: 25 * x, seed=10)
    # C4 tail: any OTHER taught skill marked stale by the fixpoint (e.g. แปดเท่า if its
    # stored program calls quad) is recorded and revalidated to its recomposed behavior.
    expect = {'สองเท่า': 2, 'สี่เท่า': 5, 'สิบหกเท่า': 25}
    prov8 = h.mem.skills['แปดเท่า'][2]
    out['c4_eight_stale'] = 'stale' in prov8
    if 'stale' in prov8:
        fn8 = h.mem.skills['แปดเท่า'][1]  # run() resolves names live = recomposed behavior
        r = revalidate(h, 'แปดเท่า', lambda x: fn8(x, 1))
        out['c4_eight_reval'] = r['kind']
        assert fn8(3, 1) % 3 == 0
        expect['แปดเท่า'] = fn8(3, 1) // 3
        out['c4_eight_probe'] = probe(h, 'แปดเท่า', lambda x: expect['แปดเท่า'] * x, seed=11)
    else:
        expect['แปดเท่า'] = 8
        out['c4_eight_probe'] = probe(h, 'แปดเท่า', lambda x: 8 * x, seed=11)
    out['expect'] = expect
    # 9. C2: attr battery exact after ALL numeric activity
    out['c2_battery_s1'] = battery_ok(h.mem.attrs)
    out['c2_double_post_attr'] = probe(h, 'สองเท่า', lambda x: 2 * x, seed=12)
    # 10. C6: log integrity
    out['c6_log_ok'] = all(e.get('kind') and e.get('source') for e in h.log)
    out['c6_log_n'] = len(h.log)
    h.save(PATH, extra={'expect': expect})
    return out

def s2():
    expect = pickle.load(open(PATH, 'rb'))['expect']
    h = HSML.load(PATH, seed=0); out = {'expect': expect}
    # C7: all session-1 final behaviors reproduce in the fresh process
    for i, (w, m) in enumerate(expect.items()):
        out[f'c7_probe_{w}'] = probe(h, w, (lambda mm: (lambda x: mm * x))(m), seed=30 + i)
    r = h.hear('สามเท่า ของ 5 คืออะไร'); out['c7_pre_abstain'] = r['kind']
    out['c7_battery'] = battery_ok(h.mem.attrs)
    r = h.hear('ร้อยเท่า ของ 5 คืออะไร'); out['c7_unknown_skill'] = r['kind']
    r = h.hear('เขา'); out['c7_unknown_attr'] = r['kind']
    # post-load teaching continues the same conversation
    r = teach(h, 'สามเท่า', lambda x: 3 * x, seed=40)
    out['c7_three_stored'] = (r['kind'] == 'skill_stored'); out['c7_three_tried'] = r.get('tried')
    out['c7_three_probe'] = probe(h, 'สามเท่า', lambda x: 3 * x, seed=41)
    # bounded garbage control (B-534 Amendment 1 lesson: 60,000/round, not the full cap)
    h.induce_cap = 60000
    grng = random.Random(555); memo = {}
    def gtruth(x):
        if x not in memo: memo[x] = grng.randrange(0, 1000)
        return memo[x]
    r = teach(h, 'เก้าเท่า', gtruth, seed=42)
    out['c7_garbage'] = {'kind': r['kind'], 'tried': r.get('tried'), 'cap': h.induce_cap}
    r = h.hear('เก้าเท่า ของ 5 คืออะไร'); out['c7_garbage_abstains'] = r['kind']
    out['c6_log_ok'] = all(e.get('kind') and e.get('source') for e in h.log)
    out['c6_log_n'] = len(h.log)
    return out

def run():
    outs = {}
    for mode in ('s1', 's2'):
        cache = f'logs/b540_{mode}.json'  # session json cached: sandbox-safe chunked runs
        if os.path.exists(cache):
            outs[mode] = json.load(open(cache))
        else:
            p = subprocess.run([sys.executable, '-u', 'b540.py', mode], capture_output=True, text=True)
            assert p.returncode == 0, (mode, p.stderr)
            outs[mode] = json.loads(p.stdout.strip().splitlines()[-1])
    s1, s2 = outs['s1'], outs['s2']
    checks = {
        'c1': (s1['quad_stored'] and s1['c1_quad_probe'] == '10/10'
               and s1['chk']['quad_naming'] == 'naming' and s1['chk']['quad_ex2'] == 'example'
               and s1['chk']['interleave_obs'] == 'observed'
               and s1['chk']['interleave_attr'] == ['attr_answer', 'unique']
               and s1['chk']['interleave_double'] == ['skill_answer', 14]),
        'c2': s1['c2_battery_s1'] and s2['c7_battery'] and s1['c2_double_post_attr'] == '10/10',
        'c3': (s1['c3_eight_stored'] and s1['c3_eight_probe'] == '10/10'
               and s1['c3_five_abstain'] == 'abstain'),
        'c4': (s1['c4_quad_revised'] and s1['c4_16_response'] == 'stale_skill'
               and s1['c4_double_unaffected'] == '10/10' and s1['c4_quad_probe'] == '10/10'
               and s1['c4_attr_after_revision'] == ['attr_answer', 'ambiguous']
               and s1['c4_reval_kind'] == 'skill_revalidated' and s1['c4_16_probe'] == '10/10'
               and (not s1['c4_eight_stale'] or s1.get('c4_eight_reval') == 'skill_revalidated')
               and s1['c4_eight_probe'] == '10/10'),
        'c5': s1['c5_unknown_skill'] == 'abstain' and s1['c5_unknown_attr'] == 'abstain',
        'c6': s1['c6_log_ok'] and s2['c6_log_ok'],
        'c7': (all(s2[f'c7_probe_{w}'] == '10/10' for w in s2['expect'])
               and s2['c7_pre_abstain'] == 'abstain'
               and s2['c7_unknown_skill'] == 'abstain' and s2['c7_unknown_attr'] == 'abstain'
               and s2['c7_three_stored'] and s2['c7_three_probe'] == '10/10'
               and s2['c7_garbage']['kind'] == 'teach_failed'
               and s2['c7_garbage_abstains'] == 'abstain'),
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
