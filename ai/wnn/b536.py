"""B-536: execution-LIB vs induction-LIB separation. LEDGER pre-reg 2026-10-25 + Amendment 1.
Arm A (full pinned-12 search space) vs Arm B (separated: primitives + dialog-taught skills).
Each arm runs in a CLEAN subprocess (module-global LIB must not leak between arms).
Amendment 1: arm A's 16n teach is budget-matched to arm B's tried (--cap16)."""
import json, re, subprocess, sys
from hsml import HSML

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

def probe(h, word, truth, n=40, seed=11):
    rng = __import__('random').Random(seed); ok = 0
    for _ in range(n):
        u = rng.randrange(400, 4000)
        r = h.hear(f'{word} ของ {u} คืออะไร')
        ok += (r['kind'] == 'skill_answer' and r.get('result') == truth(u))
    return f'{ok}/{n}'

def arm(mode, cap16=None):
    h = HSML(seed=0, induction_lib=('full' if mode == 'armA' else 'separated'))
    out = {'arm': mode}
    for word, truth in (('สองเท่า', lambda x: 2 * x), ('สี่เท่า', lambda x: 4 * x)):
        r = teach_via_dialog(h, word, truth)
        out[f'{word}_stored'] = (r['kind'] == 'skill_stored')
        out[f'{word}_tried'] = r.get('tried')
        out[f'{word}_probe'] = probe(h, word, truth)
    if cap16 is not None:
        h.induce_cap = cap16
    r = teach_via_dialog(h, 'สิบหกเท่า', lambda x: 16 * x)
    out['s16_stored'] = (r['kind'] == 'skill_stored')
    out['s16_tried'] = r.get('tried')
    if out['s16_stored']:
        out['s16_probe'] = probe(h, 'สิบหกเท่า', lambda x: 16 * x)
        # did the stored 16n program CALL quad? (reuse evidence, B-531 style)
        prog = h.mem.skills['สิบหกเท่า'][0]
        out['s16_calls_quad'] = 'สี่เท่า' in str(prog)
    return out

def garbage():
    h = HSML(seed=1, induction_lib='separated')
    grng = __import__('random').Random(555); memo = {}
    def gtruth(x):
        if x not in memo: memo[x] = grng.randrange(0, 1000)
        return memo[x]
    r = teach_via_dialog(h, 'สามเท่า', gtruth)
    return {'c5_final_kind': r['kind'], 'c5_tried': r.get('tried'), 'cap': 700001}

def run():
    b = subprocess.run([sys.executable, '-u', 'b536.py', 'armB'], capture_output=True, text=True)
    assert b.returncode == 0, b.stderr
    armB = json.loads(b.stdout.strip().splitlines()[-1])
    cap16 = armB['s16_tried'] if armB['s16_tried'] else 700001
    a = subprocess.run([sys.executable, '-u', 'b536.py', 'armA', str(cap16)], capture_output=True, text=True)
    assert a.returncode == 0, a.stderr
    armA = json.loads(a.stdout.strip().splitlines()[-1])
    g = subprocess.run([sys.executable, '-u', 'b536.py', 'garbage'], capture_output=True, text=True)
    assert g.returncode == 0, g.stderr
    gar = json.loads(g.stdout.strip().splitlines()[-1])
    out = {'armA': armA, 'armB': armB, 'c5_details': gar, 'cap16_budget_matched': cap16}
    checks = {
        'c1': all(out[x][f'{w}_stored'] for x in ('armA', 'armB') for w in ('สองเท่า', 'สี่เท่า')),
        'c2': armB['s16_stored'] and armB.get('s16_calls_quad', False),
        'c3': all(out[x].get(f'{w}_probe') == '40/40' for x in ('armA', 'armB') for w in ('สองเท่า', 'สี่เท่า')) and (not armB['s16_stored'] or armB.get('s16_probe') == '40/40'),
        'c4_leq': all((armB[f'{w}_tried'] or 10**18) <= (armA[f'{w}_tried'] or 10**18) for w in ('สองเท่า', 'สี่เท่า')),
        'c5': gar['c5_final_kind'] == 'teach_failed' and isinstance(gar['c5_tried'], int),
    }
    out.update(checks)
    out['verdict'] = 'PASS' if all(checks.values()) else 'FAIL'
    print(json.dumps(out, ensure_ascii=False))
    print('DONE')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('armA', 'armB'):
        cap16 = int(sys.argv[2]) if len(sys.argv) > 2 else None
        print(json.dumps(arm(sys.argv[1], cap16), ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == 'garbage':
        print(json.dumps(garbage(), ensure_ascii=False))
    else:
        run()
