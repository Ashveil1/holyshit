"""B-534: one conversation entry point - teach and answer interleaved against ONE memory.
LEDGER pre-reg 2026-10-25. A single scripted CONVERSATION through HSML.hear(): teach double,
probe it, attr statements + probes, teach quad, probe both, seeded battery, garbage teacher."""
import random, json, re
from hsml import HSML, CONF_Q
from b527 import SKILLS
from b521 import gen_corpus
from b526 import battery
from cur7 import gen as cgen

def teach_via_dialog(h, word, truth, seed=0):
    rng = random.Random(seed)
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
    rng = random.Random(seed)
    ok = 0
    for _ in range(n):
        u = rng.randrange(400, 4000)
        r = h.hear(f'{word} ของ {u} คืออะไร')
        ok += (r['kind'] == 'skill_answer' and r.get('result') == truth(u))
    return f'{ok}/{n}'

def run():
    h = HSML(seed=0)
    out = {'c1_single_object': True}  # one HSML object carries the whole conversation
    # C3a: no-skill query abstains before any teaching
    r = h.hear('สองเท่า ของ 5 คืออะไร')
    out['c3_abstain_before_teaching'] = (r['kind'] == 'abstain')
    # teach double in-conversation
    r = teach_via_dialog(h, 'สองเท่า', lambda x: 2 * x)
    out['double_stored'] = (r['kind'] == 'skill_stored')
    out['double_tried'] = r.get('tried')
    # C2: double probe in the SAME conversation
    out['c2_double_probe'] = probe(h, 'สองเท่า', lambda x: 2 * x)
    # attr statements + probe, interleaved
    rng = random.Random(0)
    for s in gen_corpus(rng, 8):
        h.hear(s)
    r = h.hear('ปีก')
    out['attr_probe'] = (r['kind'], r.get('decision'))
    # teach quad in the SAME conversation
    r = teach_via_dialog(h, 'สี่เท่า', lambda x: 4 * x)
    out['quad_stored'] = (r['kind'] == 'skill_stored')
    out['quad_tried'] = r.get('tried')
    out['c2_quad_probe'] = probe(h, 'สี่เท่า', lambda x: 4 * x)
    # C4: double still correct after quad
    out['c4_double_after_quad'] = probe(h, 'สองเท่า', lambda x: 2 * x, seed=8)
    # C3b: seeded skills + battery after the mixed conversation
    c3 = {}
    for task in SKILLS:
        te = random.Random(1000); okc = n = 0
        for sc in (1, 2, 3, 4):
            for _ in range(10):
                x, y, rr = cgen(task, te, sc)
                a = h.mem.answer(f'{SKILLS[task]} ของ {x} คืออะไร')
                n += 1; okc += (a.get('kind') == 'skill_answer' and a.get('result') == rr)
        c3[task] = f'{okc}/{n}'
    out['c3_seeded'] = c3
    b = battery(h.mem.attrs)
    out['c3_attr_battery'] = {k: f'{v[0]}/{v[1]}' for k, v in b.items()}
    # C6: garbage teacher in-conversation
    grng = random.Random(555); memo = {}
    def gtruth(x):
        if x not in memo: memo[x] = grng.randrange(0, 1000)
        return memo[x]
    r = teach_via_dialog(h, 'สามเท่า', gtruth)
    out['c6_garbage'] = {'final_kind': r['kind'], 'tried': r.get('tried')}
    r = h.hear('สามเท่า ของ 5 คืออะไร')
    out['c6_garbage_abstains'] = (r['kind'] == 'abstain')
    print('C6:', out['c6_garbage'], flush=True)
    # C5: every response has a recorded memory source
    srcs = {}
    for e in h.log:
        srcs[e['source']] = srcs.get(e['source'], 0) + 1
    out['c5_sources'] = srcs
    # verdict
    c2 = out['c2_double_probe'] == '10/10' and out['c2_quad_probe'] == '10/10'
    c3 = (out['c3_abstain_before_teaching'] and all(v == '40/40' for v in out['c3_seeded'].values())
          and all(v.split('/')[0] == v.split('/')[1] for v in out['c3_attr_battery'].values()))
    c4 = out['c4_double_after_quad'] == '10/10'
    c5 = all(e['source'] for e in h.log) and 'dialog' in srcs and 'induction' in srcs
    c6 = out['c6_garbage']['final_kind'] == 'teach_failed' and out['c6_garbage_abstains']
    c1 = out['c1_single_object'] and out['double_stored'] and out['quad_stored']
    verdict = 'PASS' if all((c1, c2, c3, c4, c5, c6)) else 'FAIL'
    print(json.dumps({'verdict': verdict, 'c1': c1, 'c2': c2, 'c3': c3, 'c4': c4,
                      'c5': c5, 'c6': c6, **out}, ensure_ascii=False), flush=True)
    print('DONE', flush=True)

if __name__ == '__main__':
    run()
