"""B-600: supplied question-type router over B-598 guard. Usage: python3 b600.py"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET
from b574 import pick_tau_precision
from b598 import ChatLowBand, SCHEMA_TOKENS

EXPLAIN = {'ทำไม', 'อย่างไร', 'ยังไง', 'เพราะ'}
GRADABLE = {'สวย', 'ดี', 'ใหญ่', 'เร็ว'}

class ChatTyped(ChatLowBand):
    def __init__(self, *a):
        super().__init__(*a); self.honest_type = 0
    def turn(self, s, gold_intent, gold_slots, scripted=None):
        # SUPPLIED question-type router at turn level (before band logic):
        # explanatory and gradable-predicate turns get an honest limit with
        # NO schema confirmation. Definitions still take precedence.
        toks = set(s.split())
        if toks & EXPLAIN:
            self.honest_type += 1; self.seen.add(s)
            return 'honest_engaged', {'routed': 'explain'}
        if (toks & GRADABLE) and ('ไหม' in toks or 'หรือเปล่า' in toks):
            self.honest_type += 1; self.seen.add(s)
            return 'honest_engaged', {'routed': 'gradable'}
        return super().turn(s, gold_intent, gold_slots, scripted)

if __name__ == '__main__':
    from b599 import MIX, UNFAM
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    chat = ChatTyped(m, tau_hi, 1.0, extract)
    chat.turn_raw('ช้างเป็นสัตว์', 'teach_isa', ('ช้าง', 'สัตว์'), ('teach_isa', ('ช้าง', 'สัตว์')))
    from collections import Counter
    rows = []
    for utt, gi, gs, scripted, behav, label in MIX:
        q0 = chat.q
        cls, meta = chat.turn(utt, gi if gi != 'has_a_q?' else None, gs, scripted)
        rows.append({'turn': utt, 'cls': cls, 'asked': chat.q > q0, 'label': label,
                     'routed': meta.get('routed')})
    for r in rows: print('CASE ' + json.dumps(r, ensure_ascii=False))
    for utt, gi, gs, scripted, behav, label in UNFAM:
        q0 = chat.q
        cls, meta = chat.turn(utt, gi, gs, scripted)
        print('UNFAM ' + json.dumps({'turn': utt, 'cls': cls, 'asked': chat.q > q0}, ensure_ascii=False))
    misleading_still_asked = sum(1 for r in rows if r['label'] == 'misleading-ask' and r['asked'])
    appropriate_kept = sum(1 for r in rows if r['label'] == 'appropriate-ask' and r['asked'])
    print('SUMMARY ' + json.dumps({'misleading_still_asked': misleading_still_asked,
        'appropriate_kept': appropriate_kept, 'honest_type_routes': chat.honest_type,
        'questions_total': chat.q, 'fabricated': chat.fabricated}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
    print('DONE')
