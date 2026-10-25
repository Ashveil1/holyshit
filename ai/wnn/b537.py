"""B-537: continual teaching across sessions. LEDGER pre-reg 2026-10-25.
S1 teach double, save. S2 load, probe double pre-teach, teach quad + 16n, save.
S3 load, probe all three, provenance, cumulative state, never-taught abstain."""
import json, pickle, re, subprocess, sys
from hsml import HSML

PATH = 'logs/b537_mem.pkl'

def teach_via_dialog(h, word, truth, seed=0):
    rng = __import__('random').Random(seed)
    r = h.hear(f'วิธีนี้ชื่อ {word}')
    assert r['kind'] == 'naming', r
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
    rng = __import__('random').Random(seed); ok = 0
    for _ in range(n):
        u = rng.randrange(400, 4000)
        r = h.hear(f'{word} ของ {u} คืออะไร')
        ok += (r['kind'] == 'skill_answer' and r.get('result') == truth(u))
    return f'{ok}/{n}'

TRUTHS = {'สองเท่า': lambda x: 2 * x, 'สี่เท่า': lambda x: 4 * x, 'สิบหกเท่า': lambda x: 16 * x}  # Amendment 2

def s1():
    h = HSML(seed=0)
    out = {}
    r = teach_via_dialog(h, 'สองเท่า', TRUTHS['สองเท่า'])
    out['s1_double_stored'] = (r['kind'] == 'skill_stored'); out['s1_double_tried'] = r.get('tried')
    r = teach_via_dialog(h, 'สี่เท่า', TRUTHS['สี่เท่า'])
    out['s1_quad_stored'] = (r['kind'] == 'skill_stored'); out['s1_quad_tried'] = r.get('tried')
    h.save(PATH)
    return out

def s2():
    h = HSML.load(PATH, seed=0)
    out = {'c1_preteach_double_probe': probe(h, 'สองเท่า', TRUTHS['สองเท่า'])}
    # Amendment 2: teach 16n DIRECTLY (no fresh quad in S2) - the only short composition
    # path is via the LOADED quad (2 levels, the measured-reachable horizon).
    import cur7 as C7
    out['lib_has_loaded_double'] = 'สองเท่า' in C7.LIB
    out['lib_has_loaded_quad'] = 'สี่เท่า' in C7.LIB
    r = teach_via_dialog(h, 'สิบหกเท่า', TRUTHS['สิบหกเท่า'])
    out['s2_s16_stored'] = (r['kind'] == 'skill_stored'); out['s2_s16_tried'] = r.get('tried')
    if out['s2_s16_stored']:
        out['s16_calls_quad'] = 'สี่เท่า' in str(h.mem.skills['สิบหกเท่า'][0])
    h.save(PATH)
    return out

def s3():
    h = HSML.load(PATH, seed=0)
    out = {}
    for w, t in TRUTHS.items():
        if w in h.mem.skills:
            out[f'c3_{w}_probe'] = probe(h, w, t)
            out[f'c3_{w}_prov'] = h.mem.skills[w][2].get('source')
        else:
            out[f'c3_{w}_probe'] = 'ABSENT'
    with open(PATH, 'rb') as f: saved = pickle.load(f)
    out['c4_cumulative'] = all(w in saved['skills'] for w in TRUTHS)
    r = h.hear('เจ็ดเท่า ของ 5 คืออะไร')
    out['c5_never_taught_abstains'] = (r['kind'] == 'abstain')
    return out

def run():
    outs = {}
    for mode in ('s1', 's2', 's3'):
        p = subprocess.run([sys.executable, '-u', 'b537.py', mode], capture_output=True, text=True)
        assert p.returncode == 0, (mode, p.stderr)
        outs[mode] = json.loads(p.stdout.strip().splitlines()[-1])
    s2, s3 = outs['s2'], outs['s3']
    checks = {
        'c1': s2['c1_preteach_double_probe'] == '10/10',
        'c2': s2['s2_s16_stored'] and s2.get('s16_calls_quad', False) and s2['lib_has_loaded_double'] and s2['lib_has_loaded_quad'],
        'c3': all(s3.get(f'c3_{w}_probe') == '10/10' and s3.get(f'c3_{w}_prov') == 'dialog' for w in TRUTHS),
        'c4': s3['c4_cumulative'],
        'c5': s3['c5_never_taught_abstains'],
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
