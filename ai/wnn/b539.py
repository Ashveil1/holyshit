"""B-539: dependent-skill semantics under revision. LEDGER pre-reg + Amendment 1, 2026-10-25.
S1: teach double/quad/16n/256n; C6 failed-callee-revision control; revise quad 4n->5n;
    stale checks (direct 16n, transitive 256n); cache coherence; revalidate-accept 16n;
    revalidate-reject 256n -> revision re-teach (10n); revise quad again (rev 2); save.
S2: fresh process - stale marks persist, quad rev 2, post-load revalidation (36n)."""
import json, random, re, subprocess, sys
from hsml import HSML
import cur7 as C7

PATH = 'logs/b539_mem.pkl'

def teach(h, word, truth, seed=0, name=True):
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

def revalidate(h, word, truth):
    r = h.hear(f'วิธีนี้ชื่อ {word}')
    assert r['kind'] == 'revalidate_opened', r
    n = 0
    while r['kind'] == 'revalidate_opened' or (r['kind'] == 'confirmation_question'):
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

def s1():
    h = HSML(seed=0); out = {}
    out['tried'] = {}
    for w, t, sd in (('สองเท่า', lambda x: 2*x, 0), ('สี่เท่า', lambda x: 4*x, 1),
                     ('สิบหกเท่า', lambda x: 16*x, 2), ('สองห้าหกเท่า', lambda x: 256*x, 3)):
        r = teach(h, w, t, seed=sd)
        out[f'{w}_stored'] = (r['kind'] == 'skill_stored'); out['tried'][w] = r.get('tried')
    # C1: dependency provenance
    p16 = h.mem.skills['สิบหกเท่า'][2]; p256 = h.mem.skills['สองห้าหกเท่า'][2]
    out['c1_16_deps'] = p16.get('deps'); out['c1_16_dep_rev'] = p16.get('dep_rev')
    out['c1_256_deps'] = p256.get('deps')
    # C8-pre: probe quad pre-revision (fills ev cache for these inputs)
    out['c8_pre_quad'] = probe(h, 'สี่เท่า', lambda x: 4*x, seed=21)
    # C6: failed-callee-revision control (garbage, full cap) BEFORE any successful revision
    h.hear('วิธีนี้ชื่อ สี่เท่า')
    grng = random.Random(555); memo = {}
    def gtruth(x):
        if x not in memo: memo[x] = grng.randrange(0, 1000)
        return memo[x]
    r = teach(h, 'สี่เท่า', gtruth, seed=5, name=False)
    out['c6_kind'] = r['kind']; out['c6_tried'] = r.get('tried')
    out['c6_16_not_stale'] = 'stale' not in h.mem.skills['สิบหกเท่า'][2]
    out['c6_16_probe'] = probe(h, 'สิบหกเท่า', lambda x: 16*x, seed=22)
    # C2: revise quad 4n -> 5n
    h.hear('วิธีนี้ชื่อ สี่เท่า')
    r = teach(h, 'สี่เท่า', lambda x: 5*x, seed=6, name=False)
    out['c2_quad_revised'] = (r['kind'] == 'skill_stored'); out['c2_tried'] = r.get('tried')
    qprov = h.mem.skills['สี่เท่า'][2]
    out['c2_quad_rev'] = qprov.get('revision'); out['c2_quad_replaces'] = 'replaces' in qprov
    st16 = h.mem.skills['สิบหกเท่า'][2].get('stale'); st256 = h.mem.skills['สองห้าหกเท่า'][2].get('stale')
    out['c2_16_stale'] = st16; out['c9_256_stale'] = st256
    # C3 + C9: explicit stale responses, LIB exclusion, no crash
    r = h.hear('สิบหกเท่า ของ 5 คืออะไร'); out['c3_16_response'] = r['kind']
    r = h.hear('สองห้าหกเท่า ของ 5 คืออะไร'); out['c9_256_response'] = r['kind']
    out['c3_16_in_lib'] = 'สิบหกเท่า' in C7.LIB; out['c9_256_in_lib'] = 'สองห้าหกเท่า' in C7.LIB
    # C8: cache coherence - same pre-revision inputs, new behavior
    out['c8_post_quad_same_inputs'] = probe(h, 'สี่เท่า', lambda x: 5*x, seed=21)
    # C4: revalidate-accept 16n (recomposed 25n)
    r = revalidate(h, 'สิบหกเท่า', lambda x: 25*x)
    out['c4_kind'] = r['kind']
    out['c4_16_probe'] = probe(h, 'สิบหกเท่า', lambda x: 25*x, seed=23)
    p16 = h.mem.skills['สิบหกเท่า'][2]
    out['c4_stale_cleared'] = 'stale' not in p16
    out['c4_dep_rev'] = p16.get('dep_rev'); out['c4_revalidated'] = p16.get('revalidated')
    out['c4_16_in_lib'] = 'สิบหกเท่า' in C7.LIB
    out['c9_256_still_stale'] = 'stale' in h.mem.skills['สองห้าหกเท่า'][2]
    # C5: revalidate-reject 256n -> revision; re-teach target 10n (Amendment 1)
    r = h.hear('วิธีนี้ชื่อ สองห้าหกเท่า')
    out['c5_revalidate_opened'] = (r['kind'] == 'revalidate_opened')
    cx = int(re.fullmatch(r'ถ้า n เป็น (\d+) ตอบอะไร', r['text']).group(1))
    r = h.hear(f'ตอบ {256*cx}')  # teacher rejects recomposed (625n), wants 256n semantics...
    # ...but 256n is unreachable in the post-revision LIB (Amendment 1): the revision
    # re-teach target is what the teacher then actually teaches - 10n examples.
    out['c5_reject_continues'] = (r['kind'] == 'example')
    r = teach(h, 'สองห้าหกเท่า', lambda x: 10*x, seed=7, name=False)
    out['c5_stored'] = (r['kind'] == 'skill_stored'); out['c5_tried'] = r.get('tried')
    out['c5_new_probe'] = probe(h, 'สองห้าหกเท่า', lambda x: 10*x, seed=24)
    p256 = h.mem.skills['สองห้าหกเท่า'][2]
    out['c5_revision'] = p256.get('revision'); out['c5_replaces'] = 'replaces' in p256
    out['c5_stale_cleared'] = 'stale' not in p256
    # C7 setup: revise quad again (5n -> 6n, revision 2) to re-stale 16n, then save
    h.hear('วิธีนี้ชื่อ สี่เท่า')
    r = teach(h, 'สี่เท่า', lambda x: 6*x, seed=8, name=False)
    out['c7_quad_rev2'] = h.mem.skills['สี่เท่า'][2].get('revision')
    out['c7_16_stale_again'] = 'stale' in h.mem.skills['สิบหกเท่า'][2]
    out['c7_256_stale_again'] = 'stale' in h.mem.skills['สองห้าหกเท่า'][2]
    h.save(PATH)
    return out

def s2():
    h = HSML.load(PATH, seed=0); out = {}
    r = h.hear('สิบหกเท่า ของ 5 คืออะไร'); out['c7_16_response'] = r['kind']
    out['c7_16_in_lib'] = 'สิบหกเท่า' in C7.LIB
    out['c7_quad_rev'] = h.mem.skills['สี่เท่า'][2].get('revision')
    out['c7_quad_probe'] = probe(h, 'สี่เท่า', lambda x: 6*x, seed=25)
    # post-load revalidation of 16n: recomposed 36n (6*6)
    r = revalidate(h, 'สิบหกเท่า', lambda x: 36*x)
    out['c7_reval_kind'] = r['kind']
    out['c7_16_probe'] = probe(h, 'สิบหกเท่า', lambda x: 36*x, seed=26)
    p16 = h.mem.skills['สิบหกเท่า'][2]
    out['c7_dep_rev'] = p16.get('dep_rev'); out['c7_revalidated'] = p16.get('revalidated')
    out['c7_16_in_lib_after'] = 'สิบหกเท่า' in C7.LIB
    return out

def run():
    outs = {}
    for mode in ('s1', 's2'):
        p = subprocess.run([sys.executable, '-u', 'b539.py', mode], capture_output=True, text=True)
        assert p.returncode == 0, (mode, p.stderr)
        outs[mode] = json.loads(p.stdout.strip().splitlines()[-1])
    s1, s2 = outs['s1'], outs['s2']
    checks = {
        'c1': s1['c1_16_deps'] == ['สี่เท่า'] and s1['c1_16_dep_rev'] == {'สี่เท่า': 0} and s1['c1_256_deps'] == ['สิบหกเท่า'],
        'c2': s1['c2_quad_revised'] and s1['c2_quad_rev'] == 1 and s1['c2_quad_replaces'] and s1['c2_16_stale'] == {'dep': 'สี่เท่า', 'from_revision': 0, 'to_revision': 1},
        'c3': s1['c3_16_response'] == 'stale_skill' and not s1['c3_16_in_lib'],
        'c4': s1['c4_kind'] == 'skill_revalidated' and s1['c4_16_probe'] == '10/10' and s1['c4_stale_cleared'] and s1['c4_dep_rev'] == {'สี่เท่า': 1} and s1['c4_revalidated'] == 1 and s1['c4_16_in_lib'],
        'c5': s1['c5_revalidate_opened'] and s1['c5_reject_continues'] and s1['c5_stored'] and s1['c5_new_probe'] == '10/10' and s1['c5_revision'] == 1 and s1['c5_replaces'] and s1['c5_stale_cleared'],
        'c6': s1['c6_kind'] == 'teach_failed' and s1['c6_tried'] == 700001 and s1['c6_16_not_stale'] and s1['c6_16_probe'] == '10/10',
        'c7': s2['c7_16_response'] == 'stale_skill' and not s2['c7_16_in_lib'] and s2['c7_quad_rev'] == 2 and s2['c7_quad_probe'] == '10/10' and s2['c7_reval_kind'] == 'skill_revalidated' and s2['c7_16_probe'] == '10/10' and s2['c7_dep_rev'] == {'สี่เท่า': 2} and s2['c7_16_in_lib_after'],
        'c8': s1['c8_pre_quad'] == '10/10' and s1['c8_post_quad_same_inputs'] == '10/10',
        'c9': s1['c9_256_stale'] == {'dep': 'สี่เท่า', 'from_revision': 0, 'to_revision': 1} and s1['c9_256_response'] == 'stale_skill' and not s1['c9_256_in_lib'] and s1['c9_256_still_stale'],
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
