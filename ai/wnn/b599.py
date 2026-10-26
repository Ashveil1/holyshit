"""B-599: appropriateness assessment, unpatched B-598 guard. Usage: python3 b599.py"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET
from b574 import pick_tau_precision
from b598 import ChatLowBand

# (surface, gold, slots, scripted, expected_behavior_class, appropriateness_if_asked)
MIX = [
    ('ทำไม ช้าง เป็น สัตว์', None, None, None, 'ask', 'misleading-ask'),
    ('ช้าง เป็น สัตว์ อย่างไร', None, None, None, 'ask', 'misleading-ask'),
    ('ช้าง สวย ไหม', None, None, None, 'ask', 'misleading-ask'),
    ('ช้าง ดี ไหม', None, None, None, 'ask', 'misleading-ask'),
    ('ช้าง ชอบ กิน อะไร', None, None, None, 'ask', 'misleading-ask'),
    ('ช้าง อยาก บิน', None, None, None, 'silent', 'silent-ok'),
    ('แล้ว ช้าง ล่ะ มี งา ไหม', 'has_a_q?', None, None, 'ask', 'appropriate-ask'),
    ('ช้าง มี งา หรือเปล่า', None, None, None, 'ask', 'appropriate-ask'),
    ('ราคา เท่าไหร่ กัน', None, None, None, 'silent', 'silent-ok'),
    ('ฝน ตก หนัก มาก', None, None, None, 'silent', 'silent-ok'),
]
# unfamiliar-composition set: SEPARATE, not for refinement decisions
UNFAM = [
    ('สัตว์ ที่ ช้าง เป็น คืออะไร', None, None, None, 'any', 'composition-1'),
    ('งา ของ ช้าง มี ไหม', None, None, None, 'any', 'composition-2'),
    ('ช้าง เป็น สัตว์ ใช่ หรือ ไม่', None, None, None, 'any', 'composition-3'),
]

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    chat = ChatLowBand(m, tau_hi, 1.0, extract)
    chat.turn_raw('ช้างเป็นสัตว์', 'teach_isa', ('ช้าง', 'สัตว์'), ('teach_isa', ('ช้าง', 'สัตว์')))
    rows = []
    for utt, gi, gs, scripted, behav, label in MIX:
        q0 = chat.q
        cls, meta = chat.turn(utt, gi if gi != 'has_a_q?' else None, gs, scripted)
        asked = chat.q > q0
        actual = 'ask' if asked else 'silent'
        rows.append({'turn': utt, 'cls': cls, 'asked': asked, 'expected_behavior': behav,
                     'appropriateness': label, 'fabricated_action': cls in ('teach_ok','answer_ok','inference_ok') and gi in (None, 'has_a_q?')})
    for r in rows: print('CASE ' + json.dumps(r, ensure_ascii=False))
    urows = []
    for utt, gi, gs, scripted, behav, label in UNFAM:
        q0 = chat.q
        cls, meta = chat.turn(utt, gi, gs, scripted)
        urows.append({'turn': utt, 'cls': cls, 'asked': chat.q > q0, 'note': label})
    for r in urows: print('UNFAM ' + json.dumps(r, ensure_ascii=False))
    from collections import Counter
    agg = Counter(r['appropriateness'] for r in rows if r['asked'])
    print('SUMMARY ' + json.dumps({'asked_by_label': dict(agg),
        'silent_cases': sum(1 for r in rows if not r['asked']),
        'fabricated': sum(r['fabricated_action'] for r in rows),
        'questions_total': chat.q}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
    print('DONE')
