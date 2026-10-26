"""B-602: entity canonicalization - unassisted correctness on unseen entities.
Usage: python3 b602.py
"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET
from b574 import pick_tau_precision
from b592 import HSMLChat

def canon(s, ents):
    return ' '.join('<ENT>' if t in ents else t for t in s.split())

def enc_union(s, ents):
    f = B.encode(s)
    if ents:
        for k, v in B.encode(canon(s, ents)).items():
            f[k] = f.get(k, 0) + v
    return f

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    train_ents = set(x for s, d, slots, _ in train for x in slots)
    # --- frozen protocol: baseline S1 vs canonical-union ---
    m0 = NBu(B.INTENTS)
    for s, d, _, _ in train: m0.add(B.encode(s), d)
    m1 = NBu(B.INTENTS)
    for s, d, _, _ in train: m1.add(enc_union(s, train_ents), d)
    def acc(m, data, ents=None):
        ok = 0
        for s, d, _, _ in data:
            f = enc_union(s, ents) if ents else B.encode(s)
            p, mg = B.predict(m, f, -1e18)
            ok += p == d
        return ok / len(data)
    base_dev, base_ev, base_wrong = acc(m0, dev), acc(m0, ev), acc(m0, ev_wrong)
    cu_dev, cu_ev, cu_wrong = acc(m1, dev, train_ents), acc(m1, ev, train_ents), acc(m1, ev_wrong, train_ents)
    # --- battery: bootstrapped entities in trained frames, unassisted rate ---
    tau_hi, _ = pick_tau_precision(m0, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    BATTERY = [('ช้าง เป็น สัตว์', 'teach_isa', ('ช้าง', 'สัตว์')), ('ช้าง มี งา', 'teach_attr', ('ช้าง', 'งา')),
               ('เสือ เป็น สัตว์', 'teach_isa', ('เสือ', 'สัตว์')), ('เสือ มี เขา', 'teach_attr', ('เสือ', 'เขา')),
               ('หมู มี ขน', 'teach_attr', ('หมู', 'ขน')), ('ช้าง เป็น สัตว์ ไหม', 'is_a_q', ('ช้าง', 'สัตว์')),
               ('เสือ เป็น นก ไหม', 'is_a_q', ('เสือ', 'นก')), ('หาง ของ ช้าง คืออะไร', 'ask_attr', ('ช้าง', 'หาง')),
               ('หมู ไม่มี ขน', 'retract_attr', ('หมู', 'ขน')), ('ม้า เป็น สัตว์', 'teach_isa', ('ม้า', 'สัตว์')),
               ('ช้าง มี งา ไหม หรือเปล่า', None, None), ('ราคา เท่าไหร่ กัน', None, None)]
    out = {}
    for mode in ('raw', 'canon'):
        chat = HSMLChat(m0 if mode == 'raw' else m1, tau_hi, 1.0, extract)
        ents = set(train_ents) | {'ช้าง', 'เสือ', 'หมู'}
        if mode == 'canon':
            orig_predict = B.predict
            chat_ents = ents
        unassisted_ok = 0; assisted = 0; wrong = 0; honest = 0
        for s, gi, gs in BATTERY:
            if gi is None and s.startswith('ราคา'):
                cls, meta = chat.turn(s, None, None)
                honest += cls == 'honest_engaged'
                continue
            if mode == 'canon':
                p, mg = B.predict(m1, enc_union(s, ents), -1e18)
            else:
                p, mg = B.predict(m0, B.encode(s), -1e18)
            sl = extract(s, p) if p else None
            acted_unassisted = p == gi and sl is not None and tuple(sl) == tuple(gs) and mg >= tau_hi
            if acted_unassisted: unassisted_ok += 1
            elif p is None or mg < tau_hi: assisted += 1
            else: wrong += 1
        out[mode] = {'unassisted_correct': unassisted_ok, 'needs_confirmation': assisted, 'wrong': wrong, 'honest_offtopic': honest}
    print('PROTOCOL ' + json.dumps({'base': {'dev': round(base_dev,3), 'eval': round(base_ev,3), 'ev_wrong': round(base_wrong,3)},
        'canon_union': {'dev': round(cu_dev,3), 'eval': round(cu_ev,3), 'ev_wrong': round(cu_wrong,3)}}, ensure_ascii=False))
    print('BATTERY ' + json.dumps(out, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
    print('DONE')
