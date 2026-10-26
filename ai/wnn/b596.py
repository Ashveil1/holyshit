"""B-596: out-of-lexicon degradation end-to-end. Usage: python3 b596.py"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET
from b574 import pick_tau_precision
from b592 import HSMLChat
from b589 import LEX, segment

CASES = [
    # (despaced_surface, gold_intent, gold_slots, scripted, expect_class, note)
    ('ช้างเป็นสัตว์', 'teach_isa', ('ช้าง', 'สัตว์'), ('teach_isa', ('ช้าง', 'สัตว์')), 'teach_ok', 'unknown word ช้าง, in-schema'),
    ('ปูใบไม้มีหนาม', None, None, None, 'honest', 'garbage-ish unknown'),
    ('แมวกินปลา', None, None, None, 'honest', 'in-lexicon words, no schema intent (กิน not an intent)'),
    ('โรงเรียนของฉันใหญ่', None, None, None, 'honest', 'fully unknown'),
    ('เสือมีเขา', 'teach_attr', ('เสือ', 'เขา'), ('teach_attr', ('เสือ', 'เขา')), 'teach_ok', 'unknown subject, known predicate'),
    ('มิโลชอบนอน', None, None, None, 'honest', 'known entity, unknown verb'),
    ('อากาศวันนี้ดีมาก', None, None, None, 'honest', 'transposed word order, in-lexicon'),
    ('นกเพกวินบินไม่ได้', None, None, None, 'honest', 'compound unknown'),
    ('กวางน่ะเป็นสัตว์', 'teach_isa', ('กวาง', 'สัตว์'), ('teach_isa', ('กวาง', 'สัตว์')), 'teach_ok', 'definition-reliant (def taught in setup)'),
    ('มันกินปลาไหม', None, None, None, 'ask', 'anaphora de-spaced, no context -> clarify'),
    ('สวัสดีครับวันนี้', None, None, None, 'honest', 'greeting with unknown particle ครับ'),
    ('หมูมีขน', 'teach_attr', ('หมู', 'ขน'), ('teach_attr', ('หมู', 'ขน')), 'teach_ok', 'unknown subject known attr'),
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
    chat = HSMLChat(m, tau_hi, 1.0, extract)
    # setup: teach one definition for the น่ะ pattern
    chat.turn('นิยาม เหยี่ยว น่ะ เป็น นก เหมือน เหยี่ยว เป็น นก ตัวแปร 1,4', None, None)
    ok = 0; rows = []
    for surf, gi, gs, scripted, expect, note in CASES:
        seg = ' '.join(segment(surf, LEX))
        cls, meta = chat.turn(seg, gi, gs, scripted)
        wrong_action = cls in ('teach_ok', 'answer_ok', 'inference_ok') and (gi is None or cls == 'literal_repeat')
        if expect == 'teach_ok': good = (cls == 'teach_ok')
        elif expect == 'ask': good = (cls == 'ask_needed')
        else: good = cls in ('honest_engaged', 'ask_needed')
        good = good and not (wrong_action and gi is None)
        ok += good
        rows.append({'surface': surf, 'seg': seg[:42], 'cls': cls, 'expect': expect, 'ok': good, 'note': note})
    for r in rows: print('CASE ' + json.dumps(r, ensure_ascii=False))
    print('SUMMARY ' + json.dumps({'ok': ok, 'cases': len(CASES),
        'questions_total': chat.q, 'fabricated': chat.fabricated}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
    print('DONE')
