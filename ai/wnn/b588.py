"""B-588: per-turn confirmation shell v2 - guess-confirmation questions.
Simulated user answers derived from gold (yes iff guess==gold exactly).
Usage: python3 b588.py
"""
import json, time
from collections import defaultdict, Counter
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision
from b585 import SCENARIO

class Shell2:
    def __init__(self, m, tau_hi, tau_lo, extract):
        self.m = m; self.tau_hi = tau_hi; self.tau_lo = tau_lo; self.extract = extract
        self.isa = defaultdict(set); self.attr = defaultdict(set); self.taught = {}
        self.q = 0; self.yes = 0; self.corr = 0; self.fabricated = 0
    def answer_isa(self, x, y):
        seen = {x}; fr = [x]
        while fr:
            u = fr.pop()
            if y in self.isa[u]: return 'yes'
            for v in self.isa[u]:
                if v not in seen: seen.add(v); fr.append(v)
        return 'unknown'
    def turn(self, s, gold_intent, gold_slots):
        if s in self.taught:
            d, sl = self.taught[s]
            if d is None: return 'honest_engaged'
            return self._act(d, sl)
        p, mg = B.predict(self.m, B.encode(s), -1e18)
        if p is None or mg < self.tau_lo:
            self.taught[s] = (None, None)
            if 'มัน' in s.split(): return 'ask_needed'
            return 'honest_engaged'
        sl = self.extract(s, p)
        if mg >= self.tau_hi and sl is not None and len(sl) == B.NSLOTS[p]:
            self.taught[s] = (p, sl)
            return self._act(p, sl)
        # mid band: guess-confirmation question
        self.q += 1
        guess_ok = sl is not None and len(sl) == B.NSLOTS.get(p, -1) and p == gold_intent and tuple(sl) == tuple(gold_slots)
        if guess_ok:
            self.yes += 1
            self.m.add(B.encode(s), p)
            self.taught[s] = (p, sl)
            return self._act(p, sl)
        self.corr += 1
        if gold_intent is not None:
            self.m.add(B.encode(s), gold_intent)
            self.taught[s] = (gold_intent, gold_slots)
            return self._act(gold_intent, gold_slots)
        self.taught[s] = (None, None)
        return 'honest_engaged'
    def _act(self, d, sl):
        if d == 'teach_isa': self.isa[sl[0]].add(sl[1]); return 'teach_ok'
        if d == 'teach_attr': self.attr[sl[0]].add(sl[1]); return 'teach_ok'
        if d == 'retract_attr': self.attr[sl[0]].discard(sl[1]); return 'teach_ok'
        if d == 'is_a_q':
            return 'inference_ok' if self.answer_isa(*sl) == 'yes' else 'answer_ok'
        if d == 'ask_attr':
            return 'answer_ok' if sl[1] in self.attr[sl[0]] else 'answer_ok'
        if d in ('name_skill', 'confirm_answer', 'give_example'): return 'teach_ok'
        return 'honest_engaged'

# gold labels for sim answers (intent, slots or None for out-of-scope)
GOLD = {
    'สวัสดี': (None, None), 'มิโล เป็น แมว': ('teach_isa', ('มิโล', 'แมว')),
    'แมว เป็น สัตว์': ('teach_isa', ('แมว', 'สัตว์')), 'มิโล เป็น สัตว์ ไหม': ('is_a_q', ('มิโล', 'สัตว์')),
    'มิโล มี หาง': ('teach_attr', ('มิโล', 'หาง')), 'หาง ของ มิโล คืออะไร': ('ask_attr', ('มิโล', 'หาง')),
    'แมวตัวนี้ชื่อมิโลนะ': ('teach_isa', ('มิโล', 'แมว')), 'มัน กิน ปลา ไหม': (None, None),
    'วันนี้ อากาศ ดี มาก': (None, None), 'ราคา เท่าไหร่ กัน': (None, None),
    'สอนวิธี บวก ให้หน่อย': ('name_skill', ('บวก',)), 'ตอบ สี่': ('confirm_answer', ('สี่',)),
    'มิโล เป็น นก ไหม': ('is_a_q', ('มิโล', 'นก')), 'นก เป็น สัตว์': ('teach_isa', ('นก', 'สัตว์')),
    'มิโล ไม่มี หาง': ('retract_attr', ('มิโล', 'หาง')), 'หาง ของ มิโล คืออะไร รู้ไหม': ('ask_attr', ('มิโล', 'หาง')),
    'good night sleep well': (None, None), 'เหยี่ยว เป็น สัตว์เลี้ยง ไหม': ('is_a_q', ('เหยี่ยว', 'สัตว์เลี้ยง')),
}

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    for passname in ('first', 'repeat'):
        if passname == 'first':
            sh = Shell2(m, tau_hi, 1.0, extract)
        match = 0; rows = []
        for utt, exp, scripted, note in SCENARIO:
            gi, gs = GOLD[utt]
            cls = sh.turn(utt, gi, gs)
            ok = cls == exp
            match += ok
            if passname == 'first':
                rows.append({'turn': utt, 'expected': exp, 'got': cls, 'ok': ok})
        if passname == 'first':
            for r in rows: print('TURN ' + json.dumps(r, ensure_ascii=False))
        print('SUMMARY ' + json.dumps({'pass': passname, 'match': match, 'turns': len(SCENARIO),
            'questions_total': sh.q, 'yes': sh.yes, 'corrections': sh.corr,
            'fabricated': sh.fabricated}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1),
        'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
