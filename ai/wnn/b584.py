"""B-584: conversational-feasibility baseline. Authored multi-turn scenario
vs a retrieval-first hybrid shell. Measurement only, no gate.
Usage: python3 b584.py
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
from b576 import pick_tau_accuracy

# AUTHORED conversational scenario: (user_turn, expected_class, detail)
# classes: greet | teach_ok | answer_ok | ask_needed | honest_fallback | inference_ok
SCENARIO = [
    ('สวัสดี', 'honest_fallback', 'greeting - no schema intent; must not fake an action'),
    ('มิโล เป็น แมว', 'teach_ok', 'seen-template teach_isa'),
    ('แมว เป็น สัตว์', 'teach_ok', 'seen-template teach_isa'),
    ('มิโล เป็น สัตว์ ไหม', 'inference_ok', 'is_a_q via transitive isa -> answer yes'),
    ('มิโล มี หาง', 'teach_ok', 'seen-template teach_attr'),
    ('หาง ของ มิโล คืออะไร', 'answer_ok', 'ask_attr seen template -> หาง'),
    ('แมวตัวนี้ชื่อมิโลนะ', 'ask_needed', 'unseen phrasing -> must ask, not guess'),
    ('มัน กิน ปลา ไหม', 'ask_needed', 'anaphora มัน - out of schema; must not bind blindly'),
    ('วันนี้ อากาศ ดี มาก', 'honest_fallback', 'off-topic -> no fake action/answer'),
    ('ราคา เท่าไหร่ กัน', 'honest_fallback', 'off-topic question'),
    ('สอนวิธี บวก ให้หน่อย', 'ask_needed', 'name_skill-adjacent unseen phrasing'),
    ('ตอบ สี่', 'teach_ok', 'seen-template confirm_answer'),
    ('มิโล เป็น นก ไหม', 'inference_ok', 'is_a_q: no isa path -> answer no/unknown honestly'),
    ('นก เป็น สัตว์', 'teach_ok', 'seen-template teach_isa'),
    ('มิโล ไม่มี หาง', 'teach_ok', 'retract_attr seen template'),
    ('หาง ของ มิโล คืออะไร รู้ไหม', 'answer_ok', 'ask_attr fresh-ish template -> after retract, should NOT answer หาง'),
    ('good night sleep well', 'honest_fallback', 'off-topic'),
    ('เหยี่ยว เป็น สัตว์เลี้ยง ไหม', 'ask_needed', 'unseen entities, unseen info -> ask/abstain honestly'),
]

def jaccard(a, b):
    sa, sb = set(a.split()), set(b.split())
    return len(sa & sb) / max(1, len(sa | sb))

class Shell:
    def __init__(self, m, tau, extract, nslots):
        self.m = m; self.tau = tau; self.extract = extract; self.nslots = nslots
        self.isa = defaultdict(set); self.attr = defaultdict(set)
        self.taught = []  # (utterance, intent, slots) - learned store
    def answer_isa(self, x, y):
        seen = {x}; frontier = [x]
        while frontier:
            u = frontier.pop()
            if y in self.isa[u]: return 'yes'
            for v in self.isa[u]:
                if v not in seen: seen.add(v); frontier.append(v)
        return 'unknown'
    def turn(self, s):
        # 1) retrieval over taught parses (learned store)
        best = max(((jaccard(s, t), t, d, sl) for t, d, sl in self.taught), default=(0, None, None, None))
        if best[0] >= 0.85 and best[1] != s:  # near-repeat of a taught phrasing
            _, _, d, sl = best
            return self._act(s, d, sl, via='retrieval')
        # 2) gated intent + extraction
        p, mg = B.predict(self.m, B.encode(s), -1e18)
        if p is None or mg < self.tau:
            self.taught.append((s, None, None))  # remember as unknown
            return ('honest_fallback', 'ไม่เข้าใจ/ไม่แน่ใจ - ถามกลับ')
        sl = self.extract(s, p)
        if sl is None:
            return ('ask_needed', 'สล็อตไม่ชัด - ต้องถาม')
        self.taught.append((s, p, sl))
        return self._act(s, p, sl, via='mapper')
    def _act(self, s, d, sl, via):
        if sl is None or len(sl) != self.nslots[d]:
            return ('ask_needed', 'สล็อตไม่ครบ - ต้องถาม')
        if d == 'teach_isa': self.isa[sl[0]].add(sl[1]); return ('teach_ok', 'จำ %s เป็น %s' % sl)
        if d == 'teach_attr': self.attr[sl[0]].add(sl[1]); return ('teach_ok', 'จำ %s มี %s' % sl)
        if d == 'retract_attr': self.attr[sl[0]].discard(sl[1]); return ('teach_ok', 'ลืม %s มี %s' % sl)
        if d == 'is_a_q':
            r = self.answer_isa(*sl)
            return ('inference_ok' if r == 'yes' else 'answer_ok', 'ตอบ %s (%s เป็น %s)' % (r, sl[0], sl[1]))
        if d == 'ask_attr':
            v = sl[1] if sl[1] in self.attr[sl[0]] else None
            return (('answer_ok', 'ตอบ %s' % v) if v else ('ask_needed', 'ไม่มีในความจำ - ถาม'))
        if d in ('name_skill', 'confirm_answer', 'give_example'):
            return ('teach_ok', 'รับคำสั่ง %s' % (sl[0],))
        return ('honest_fallback', 'ไม่รู้จักเจตนา')

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    seed = 0
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'precision'
    intent_tau = pick_tau_accuracy(m, dev) if mode == 'accuracy' else pick_tau_precision(m, dev)[0]
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    sh = Shell(m, intent_tau, extract, B.NSLOTS)
    counts = Counter(); log = []
    for utt, exp, note in SCENARIO:
        cls, resp = sh.turn(utt)
        ok = (cls == exp)
        counts['match' if ok else 'mismatch'] += 1
        counts['exp_' + exp] += 1
        counts['got_' + cls] += 1
        log.append({'turn': utt, 'expected': exp, 'got': cls, 'ok': ok, 'resp': resp, 'note': note})
    for l in log:
        print('TURN ' + json.dumps(l, ensure_ascii=False))
    print('SUMMARY ' + json.dumps(dict(counts), ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1),
        'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
