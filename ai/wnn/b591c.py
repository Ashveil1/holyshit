"""B-591c: definition edge cases. Usage: python3 b591c.py"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu
from b570 import Watchdog, BUDGET
from b591b import compile_def, fire

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    out = []
    # (1) redefinition: 'X น่ะ เป็น Y' first -> teach_isa; redefined -> is_a_q
    r1 = compile_def('เหยี่ยว น่ะ เป็น นก'.split(), 'เหยี่ยว เป็น นก'.split(), [0, 3])
    r2 = compile_def('เหยี่ยว น่ะ เป็น นก'.split(), 'เหยี่ยว เป็น นก ไหม'.split(), [0, 3])
    defs = [r1]
    c1 = fire(defs[-1], 'กวาง น่ะ เป็น สัตว์')
    defs.append(r2)  # latest wins policy: search reversed
    c2 = fire(defs[::-1][0] if fire(defs[::-1][0], 'กวาง น่ะ เป็น สัตว์') else defs[-1], 'กวาง น่ะ เป็น สัตว์')
    latest = next(f for f in reversed(defs) if f and fire(f, 'กวาง น่ะ เป็น สัตว์'))
    out.append({'check': 'redefinition', 'first_canonical': c1,
                'latest_canonical': fire(latest, 'กวาง น่ะ เป็น สัตว์'),
                'ok': fire(latest, 'กวาง น่ะ เป็น สัตว์') == 'กวาง เป็น สัตว์ ไหม'})
    # (2) precedence: definition on a form the grammar parses; defs fire first
    r3 = compile_def('ม้า มี ขน'.split(), 'ม้า มี ขน ไหม'.split(), [0, 2])
    defs.append(r3)
    hit = next((fire(f, 'วัว มี เขา') for f in reversed(defs) if f and fire(f, 'วัว มี เขา')), None)
    p, mg = B.predict(m, B.encode('วัว มี เขา'), -1e18)
    out.append({'check': 'precedence', 'definition_canonical': hit,
                'trained_intent_on_raw': p,
                'shadows_trained': hit is not None and hit != 'วัว มี เขา',
                'ok': hit == 'วัว มี เขา ไหม',
                'note': 'user redefined teach-looking form to mean a question; definition wins (supplied policy)'})
    # (3) question forms do not match teach definitions
    hit3 = next((fire(f, 'กวาง น่ะ เป็น สัตว์ ไหม') for f in reversed(defs) if f and fire(f, 'กวาง น่ะ เป็น สัตว์ ไหม')), None)
    out.append({'check': 'question_form_not_matched', 'hit': hit3, 'ok': hit3 is None,
                'note': 'teach definition has no ไหม constant; length differs; separate question definition required'})
    for o in out: print('CHECK ' + json.dumps(o, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
    print('DONE')
