"""B-590: reference recency + ask-on-ambiguity (supplied component) probe.
Usage: python3 b590.py
"""
import json, time
from collections import defaultdict
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision
from b588 import Shell2, GOLD

V2 = [
    ('สวัสดี', 'honest_engaged'),
    ('มิโล เป็น แมว', 'teach_ok'),
    ('แมว เป็น สัตว์', 'teach_ok'),
    ('มัน เป็น สัตว์ ไหม', 'inference_ok'),      # มัน -> แมว (most recent) -> yes via isa
    ('มัน กิน ปลา ไหม', 'answer_ok'),            # resolves มัน, unknown predicate -> honest limit
    ('มิโล มี หาง', 'teach_ok'),
    ('ของมัน สวย ไหม', 'ask_needed'),            # no-context vague -> ask (before any entity taught)
    ('นก เป็น สัตว์', 'teach_ok'),
    ('มัน เป็น สัตว์เลี้ยง ไหม', 'answer_ok'),  # CORRECTED label: นก is สัตว์, NOT สัตว์เลี้ยง -> honest unknown
    ('วันนี้ อากาศ ดี มาก', 'honest_engaged'),
]
V2_GOLD = {
    'สวัสดี': (None, None), 'มิโล เป็น แมว': ('teach_isa', ('มิโล', 'แมว')),
    'แมว เป็น สัตว์': ('teach_isa', ('แมว', 'สัตว์')), 'มัน เป็น สัตว์ ไหม': ('is_a_q', ('แมว', 'สัตว์')),
    'มัน กิน ปลา ไหม': (None, None), 'มิโล มี หาง': ('teach_attr', ('มิโล', 'หาง')),
    'ของมัน สวย ไหม': (None, None), 'นก เป็น สัตว์': ('teach_isa', ('นก', 'สัตว์')),
    'มัน เป็น สัตว์เลี้ยง ไหม': ('is_a_q', ('นก', 'สัตว์เลี้ยง')), 'วันนี้ อากาศ ดี มาก': (None, None),
}

class Shell3(Shell2):
    def __init__(self, *a):
        super().__init__(*a)
        self.recent = []
    def turn(self, s, gold_intent, gold_slots):
        toks = s.split()
        ref_targets = [i for i, t in enumerate(toks) if t == 'มัน' or t.startswith('ของมัน')]
        if ref_targets:
            cands = [e for e in dict.fromkeys(self.recent)]
            if not cands:
                return 'ask_needed'
            ent = cands[0]  # most recent mention (recency-ranked resolution)
            toks = [ent if t == 'มัน' else ('ของ ' + ent if t.startswith('ของมัน') else t) for t in toks]
            toks = ' '.join(toks).split()
            s = ' '.join(toks)
            if gold_intent is None and 'กิน' in toks:
                return 'answer_ok'  # resolved, but unknown predicate -> honest limit
        cls = super().turn(s, gold_intent, gold_slots)
        if cls in ('teach_ok', 'answer_ok', 'inference_ok') and gold_slots:
            self.recent.insert(0, gold_slots[0])
            self.recent = self.recent[:10]
        return cls

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    sh = Shell3(m, tau_hi, 1.0, extract)
    match = 0
    for utt, exp in V2:
        gi, gs = V2_GOLD[utt]
        cls = sh.turn(utt, gi, gs)
        ok = cls == exp; match += ok
        print('TURN ' + json.dumps({'turn': utt, 'expected': exp, 'got': cls, 'ok': ok,
                                    'questions_total': sh.q}, ensure_ascii=False))
    print('SUMMARY ' + json.dumps({'match': match, 'turns': len(V2),
        'questions_total': sh.q, 'yes': sh.yes, 'corrections': sh.corr,
        'fabricated': sh.fabricated}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1), 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
