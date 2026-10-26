"""B-598: low-band schema-overlap clarification. Usage: python3 b598.py"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET
from b574 import pick_tau_precision
from b588 import GOLD
from b585 import SCENARIO as V1
from b592 import HSMLChat, V3, V3_GOLD
from b597 import ChatVocab

SCHEMA_TOKENS = {'เป็น', 'มี', 'ไหม', 'คืออะไร', 'ของ', 'ไม่มี'}

class ChatLowBand(ChatVocab):
    def _pipeline(self, s, gold_intent, gold_slots, scripted):
        p, mg = B.predict(self.m, B.encode(s), -1e18)
        if p is None or mg < self.tau_lo:
            toks = set(s.split())
            known_ent = any(e in toks for e in list(self.isa) + list(self.attr)) or \
                        any(w in toks for w in getattr(self, 'vocab_learned', []))
            if (toks & SCHEMA_TOKENS) and known_ent and mg > -1e17:
                # route through the mid-band confirmation path by lowering the gate locally
                saved = self.tau_lo; self.tau_lo = -1e18
                r = HSMLChat._pipeline(self, s, gold_intent, gold_slots, scripted)
                self.tau_lo = saved
                return r
        return super()._pipeline(s, gold_intent, gold_slots, scripted)

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    # target case: bootstrap ช้าง, teach, then question
    chat = ChatLowBand(m, tau_hi, 1.0, extract)
    chat.turn_raw('ช้างเป็นสัตว์', 'teach_isa', ('ช้าง', 'สัตว์'), ('teach_isa', ('ช้าง', 'สัตว์')))
    cls, meta = chat.turn_raw('ช้างเป็นสัตว์ไหม', 'is_a_q', ('ช้าง', 'สัตว์'))
    print('TARGET ' + json.dumps({'cls': cls, 'seg': meta.get('seg'), 'questions': chat.q}, ensure_ascii=False))
    # regressions: v1 18-turn
    chat1 = ChatLowBand(m, tau_hi, 1.0, extract)
    match1 = 0; offtopic_q = 0
    for utt, exp, scripted, note in V1:
        q0 = chat1.q
        cls, _ = chat1.turn(utt, *GOLD[utt], scripted)
        match1 += cls == exp
        if exp == 'honest_engaged' and chat1.q > q0: offtopic_q += 1
    # v3 challenge
    chat3 = ChatLowBand(m, tau_hi, 1.0, extract)
    match3 = 0
    for utt, exp, scripted, _n in V3:
        q0 = chat3.q
        cls, _ = chat3.turn(utt, *V3_GOLD.get(utt, GOLD.get(utt, (None, None))), scripted)
        match3 += cls == exp
        if exp == 'honest_engaged' and chat3.q > q0: offtopic_q += 1
    print('SUMMARY ' + json.dumps({'target_recovered': cls == 'inference_ok',
        'v1_match': match1, 'v3_match': match3, 'offtopic_questions': offtopic_q,
        'fabricated': chat.fabricated + chat1.fabricated + chat3.fabricated}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
    print('DONE')
