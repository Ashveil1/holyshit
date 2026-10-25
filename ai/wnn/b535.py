"""B-535: G2 full-memory persistence across processes. LEDGER pre-reg 2026-10-25.
teach: dialog-teach double, observe attr statements, snapshot fixed probes, save, exit.
verify: clean interpreter, fresh HSML + load; behavioral recall + parity + provenance + controls."""
import json, re, subprocess, sys, pickle
from hsml import HSML

PATH = 'logs/b535_mem.pkl'
ATTR_PROBES = ['จะงอยปาก', 'ปีก', 'ขน', 'ตา', 'เขา มี ปลู๊ก']

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

def attr_snapshot(h):
    snap = {}
    for p in ATTR_PROBES:
        r = h.hear(p)
        snap[p] = (r['kind'], str(r.get('decision')))
    return snap

def mode_teach():
    from b521 import gen_corpus
    import random
    h = HSML(seed=0)
    out = {}
    r = teach_via_dialog(h, 'สองเท่า', lambda x: 2 * x)
    out['c1_double_stored'] = (r['kind'] == 'skill_stored')
    out['double_tried'] = r.get('tried')
    rng = random.Random(0)
    for s in gen_corpus(rng, 8):
        h.hear(s)
    snap = attr_snapshot(h)
    out['pre_save_probe'] = probe(h, 'สองเท่า', lambda x: 2 * x)
    h.save(PATH, extra={'attr_snapshot': snap})
    return out

def mode_verify():
    import random
    from b527 import SKILLS
    from cur7 import gen as cgen
    out = {}
    try:
        HSML.load('logs/b535_mem_missing.pkl'); out['c6_missing_err'] = False
    except (FileNotFoundError, RuntimeError) as e:
        out['c6_missing_err'] = 'missing' in str(e)
    with open(PATH + '.corrupt', 'wb') as f: f.write(b'definitely not a pickle')
    try:
        HSML.load(PATH + '.corrupt'); out['c6_corrupt_err'] = False
    except (FileNotFoundError, RuntimeError) as e:
        out['c6_corrupt_err'] = ('corrupt' in str(e)) or ('wrong format' in str(e))
    h = HSML.load(PATH, seed=0)
    out['c2_double_probe'] = probe(h, 'สองเท่า', lambda x: 2 * x)
    snap_now = attr_snapshot(h)
    with open(PATH, 'rb') as f: saved = pickle.load(f)
    out['c3_attr_parity'] = (snap_now == saved['attr_snapshot'])
    prov = h.mem.skills['สองเท่า'][2]
    out['c4_prov_dialog'] = (prov.get('source') == 'dialog')
    te = random.Random(1000); okc = n = 0
    for sc in (1, 2, 3, 4):
        for _ in range(10):
            x, y, rr = cgen('even', te, sc)
            a = h.mem.answer(f'{SKILLS["even"]} ของ {x} คืออะไร')
            n += 1; okc += (a.get('kind') == 'skill_answer' and a.get('result') == rr)
    out['c4_seeded_even'] = f'{okc}/{n}'
    r = h.hear('เจ็ดเท่า ของ 5 คืออะไร')
    out['c5_never_taught_abstains'] = (r['kind'] == 'abstain')
    return out

def run():
    t = subprocess.run([sys.executable, '-u', 'b535.py', 'teach'], capture_output=True, text=True)
    assert t.returncode == 0, t.stderr
    teach_out = json.loads(t.stdout.strip().splitlines()[-1])
    v = subprocess.run([sys.executable, '-u', 'b535.py', 'verify'], capture_output=True, text=True)
    assert v.returncode == 0, v.stderr
    ver_out = json.loads(v.stdout.strip().splitlines()[-1])
    out = {**teach_out, **ver_out}
    checks = {
        'c1': teach_out['c1_double_stored'],
        'c2': ver_out['c2_double_probe'] == '10/10',
        'c3': ver_out['c3_attr_parity'],
        'c4': ver_out['c4_prov_dialog'] and ver_out['c4_seeded_even'] == '40/40',
        'c5': ver_out['c5_never_taught_abstains'],
        'c6': ver_out['c6_missing_err'] and ver_out['c6_corrupt_err'],
    }
    out.update(checks)
    out['verdict'] = 'PASS' if all(checks.values()) else 'FAIL'
    print(json.dumps(out, ensure_ascii=False))
    print('DONE')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'teach':
        print(json.dumps(mode_teach(), ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == 'verify':
        print(json.dumps(mode_verify(), ensure_ascii=False))
    else:
        run()
