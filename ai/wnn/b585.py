"""B-585: teach-first conversational shell - clarification as the move.
Authored scenario + scripted simulated user answers. Development evidence.
Usage: python3 b585.py
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

# (user_turn, expected_class, simulated_user_answer_if_asked, note)
SCENARIO = [
    ('สวัสดี', 'honest_engaged', None, 'greeting - engage honestly, no fake action'),
    ('มิโล เป็น แมว', 'teach_ok', None, 'seen-template teach_isa'),
    ('แมว เป็น สัตว์', 'teach_ok', None, 'seen-template teach_isa'),
    ('มิโล เป็น สัตว์ ไหม', 'inference_ok', None, 'transitive isa -> yes'),
    ('มิโล มี หาง', 'teach_ok', None, 'seen teach_attr'),
    ('หาง ของ มิโล คืออะไร', 'answer_ok', None, 'ask_attr -> หาง'),
    ('แมวตัวนี้ชื่อมิโลนะ', 'teach_ok', ('teach_isa', ('มิโล', 'แมว')), 'unseen phrasing: ask -> user confirms it states Milo is a cat -> learned'),
    ('มัน กิน ปลา ไหม', 'ask_needed', None, 'anaphora - system must SAY it cannot resolve มัน yet'),
    ('วันนี้ อากาศ ดี มาก', 'honest_engaged', None, 'off-topic: engage, no fake action'),
    ('ราคา เท่าไหร่ กัน', 'honest_engaged', None, 'off-topic question: honest limit'),
    ('สอนวิธี บวก ให้หน่อย', 'teach_ok', ('name_skill', ('บวก',)), 'unseen phrasing: ask -> user confirms skill request'),
    ('ตอบ สี่', 'teach_ok', None, 'seen confirm_answer'),
    ('มิโล เป็น นก ไหม', 'answer_ok', None, 'no isa path -> honest unknown/no'),
    ('นก เป็น สัตว์', 'teach_ok', None, 'seen teach_isa'),
    ('มิโล ไม่มี หาง', 'teach_ok', None, 'retract_attr'),
    ('หาง ของ มิโล คืออะไร รู้ไหม', 'answer_ok', None, 'after retract -> must NOT say หาง'),
    ('good night sleep well', 'honest_engaged', None, 'off-topic'),
    ('เหยี่ยว เป็น สัตว์เลี้ยง ไหม', 'answer_ok', None, 'unknown entity -> honest unknown'),
]

class TeachShell:
    def __init__(self, m, tau, extract, nslots):
        self.m = m; self.tau = tau; self.extract = extract; self.nslots = nslots
        self.isa = defaultdict(set); self.attr = defaultdict(set)
        self.taught = []
    def answer_isa(self, x, y):
        seen = {x}; fr = [x]
        while fr:
            u = fr.pop()
            if y in self.isa[u]: return 'yes'
            for v in self.isa[u]:
                if v not in seen: seen.add(v); fr.append(v)
        return 'unknown'
    def turn(self, s, scripted):
        p, mg = B.predict(self.m, B.encode(s), -1e18)
        questions = 0
        if p is None or mg < self.tau:
            # in-scope-ish check: any schema token overlap with taught/train vocab?
            if scripted is not None:
                questions += 1
                d, sl = scripted
                self.m.add(B.encode(s), d)
                self.taught.append((s, d, sl))
                return self._act(d, sl), questions
            # distinguish clearly out-of-scope from unresolved-reference
            if 'มัน' in s.split():
                return ('ask_needed', 'บอกตรงๆ ว่ายังผูก "มัน" กับสิ่งที่พูดถึงก่อนหน้าไม่ได้'), questions + 1
            return ('honest_engaged', 'เรื่องนี้ยังไม่รู้/ไม่มีคำสั่ง - บอกข้อจำกัดตรงๆ'), questions
        sl = self.extract(s, p)
        if sl is None or len(sl) != self.nslots[p]:
            if scripted is not None:
                questions += 1
                d, slv = scripted
                self.m.add(B.encode(s), d)
                self.taught.append((s, d, slv))
                return self._act(d, slv), questions
            return ('ask_needed', 'ถามยืนยันความหมาย'), questions + 1
        self.taught.append((s, p, sl))
        return self._act(p, sl), questions
    def _act(self, d, sl):
        if d == 'teach_isa': self.isa[sl[0]].add(sl[1]); return ('teach_ok', 'จำ %s เป็น %s' % (sl[0], sl[1]))
        if d == 'teach_attr': self.attr[sl[0]].add(sl[1]); return ('teach_ok', 'จำ %s มี %s' % (sl[0], sl[1]))
        if d == 'retract_attr': self.attr[sl[0]].discard(sl[1]); return ('teach_ok', 'ลบ %s มี %s' % (sl[0], sl[1]))
        if d == 'is_a_q':
            r = self.answer_isa(*sl)
            return (('inference_ok', 'ตอบใช่ จากสายเหตุผล') if r == 'yes' else ('answer_ok', 'ตอบตรงๆ ว่ายังไม่มีข้อมูลว่า %s เป็น %s' % (sl[0], sl[1])))
        if d == 'ask_attr':
            return (('answer_ok', 'ตอบ %s' % sl[1]) if sl[1] in self.attr[sl[0]]
                    else ('answer_ok', 'ตอบตรงๆ ว่าไม่มีข้อมูล'))
        if d in ('name_skill', 'confirm_answer', 'give_example'):
            return ('teach_ok', 'รับคำสั่ง %s' % (sl[0],))
        return ('honest_engaged', 'ไม่รู้จักเจตนา')

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    intent_tau, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    sh = TeachShell(m, intent_tau, extract, B.NSLOTS)
    match = mismatch = totalq = 0
    for utt, exp, scripted, note in SCENARIO:
        (cls, resp), q = sh.turn(utt, scripted)
        totalq += q
        ok = cls == exp
        match += ok; mismatch += (not ok)
        print('TURN ' + json.dumps({'turn': utt, 'expected': exp, 'got': cls, 'ok': ok,
                                    'questions': q, 'resp': resp, 'note': note}, ensure_ascii=False))
    print('SUMMARY ' + json.dumps({'match': match, 'mismatch': mismatch,
                                   'total_questions': totalq, 'turns': len(SCENARIO)}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1),
        'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
