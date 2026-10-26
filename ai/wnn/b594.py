"""B-594: slot-aware mid-band confirmation vs B-592 baseline, v1 scenario.
Usage: python3 b594.py
"""
import json, time
from collections import defaultdict
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET
from b574 import pick_tau_precision
from b588 import GOLD
from b585 import SCENARIO as V1
from b592 import HSMLChat

class ChatSlot(HSMLChat):
    def __init__(self, *a):
        super().__init__(*a)
        self.partial = 0; self.full = 0; self.fields_supplied = 0
    def _pipeline(self, s, gold_intent, gold_slots, scripted):
        meta = {}
        p, mg = B.predict(self.m, B.encode(s), -1e18)
        if p is None or mg < self.tau_lo:
            if scripted is not None:
                self.q += 1
                d, sl = scripted
                if d is None: return 'honest_engaged', meta
                self.full += 1; self.fields_supplied += 1 + len(sl)
                self.m.add(B.encode(s), d)
                meta['category'] = meta.get('category') or 'teacher_assisted'
                return self._act(d, sl), meta
            return 'honest_engaged', meta
        sl = self.extract(s, p)
        if mg >= self.tau_hi and sl is not None and len(sl) == B.NSLOTS[p]:
            meta['category'] = meta.get('category') or 'unassisted'
            return self._act(p, sl), meta
        self.q += 1
        intent_ok = p == gold_intent
        slots_ok = sl is not None and len(sl) == B.NSLOTS.get(p, -1) and gold_slots is not None and tuple(sl) == tuple(gold_slots)
        if intent_ok and slots_ok:
            self.yes += 1; self.fields_supplied += 1
            self.m.add(B.encode(s), p)
            meta['category'] = meta.get('category') or 'teacher_assisted'
            return self._act(p, sl), meta
        if intent_ok and gold_slots is not None:
            # slot-targeted question: user supplies only the wrong slots
            self.partial += 1
            fixed = list(sl) if sl else [None] * B.NSLOTS[p]
            n_wrong = sum(1 for a, b in zip(fixed, gold_slots) if a != b)
            self.fields_supplied += n_wrong
            self.m.add(B.encode(s), p)
            meta['category'] = meta.get('category') or 'teacher_assisted'
            return self._act(p, gold_slots), meta
        # full correction
        self.full += 1
        if gold_intent is not None:
            self.fields_supplied += 1 + len(gold_slots)
            self.m.add(B.encode(s), gold_intent)
            meta['category'] = meta.get('category') or 'teacher_assisted'
            return self._act(gold_intent, gold_slots), meta
        return 'honest_engaged', meta

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    chat = ChatSlot(m, tau_hi, 1.0, extract)
    match = 0
    for utt, exp, scripted, note in V1:
        gi, gs = GOLD[utt]
        cls, meta = chat.turn(utt, gi, gs, scripted)
        match += cls == exp
    print('SUMMARY ' + json.dumps({'match': match, 'turns': len(V1),
        'questions_total': chat.q, 'yes': chat.yes, 'partial_corrections': chat.partial,
        'full_corrections': chat.full, 'fields_supplied_total': chat.fields_supplied,
        'fabricated': chat.fabricated,
        'baseline_b592': {'yes': 1, 'full_corrections': 13}}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
    print('DONE')
