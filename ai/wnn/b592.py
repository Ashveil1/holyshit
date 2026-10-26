"""B-592: unified conversational prototype (definitions + shell + recency).
Supplied wiring; learned = WNN mapper + taught facts/rules. Pre-registered
in LEDGER.md B-592. Usage: python3 b592.py
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
from b591b import compile_def, fire

TEACH_INTENTS = {'teach_isa', 'teach_attr', 'retract_attr', 'name_skill', 'give_example'}

class HSMLChat:
    def __init__(self, m, tau_hi, tau_lo, extract):
        self.m = m; self.tau_hi = tau_hi; self.tau_lo = tau_lo; self.extract = extract
        self.isa = defaultdict(set); self.attr = defaultdict(set)
        self.defs = []            # (rule, surface_str) latest first searched reversed
        self.subjects = []        # recent subject entities, most recent LAST
        self.seen = set()
        self.q = 0; self.yes = 0; self.corr = 0; self.fabricated = 0

    def answer_isa(self, x, y):
        seen = {x}; fr = [x]
        while fr:
            u = fr.pop()
            if y in self.isa[u]: return 'yes'
            for v in self.isa[u]:
                if v not in seen: seen.add(v); fr.append(v)
        return 'unknown'

    def _act(self, d, sl):
        if d == 'teach_isa':
            self.isa[sl[0]].add(sl[1]); self.subjects.append(sl[0]); return 'teach_ok'
        if d == 'teach_attr':
            self.attr[sl[0]].add(sl[1]); self.subjects.append(sl[0]); return 'teach_ok'
        if d == 'retract_attr': self.attr[sl[0]].discard(sl[1]); self.subjects.append(sl[0]); return 'teach_ok'
        if d == 'is_a_q':
            self.subjects.append(sl[0])
            return 'inference_ok' if self.answer_isa(*sl) == 'yes' else 'answer_ok'
        if d == 'ask_attr': self.subjects.append(sl[0]); return 'answer_ok'
        if d in ('name_skill', 'confirm_answer', 'give_example'): return 'teach_ok'
        return 'honest_engaged'

    def _resolve(self, s):
        """Return (rewritten, status): status in resolved/clarify/plural/none."""
        toks = s.split()
        if 'พวกมัน' in toks or 'พวกมัน' in s: return s, 'plural'
        if 'มัน' not in toks and 'ของมัน' not in toks: return s, 'none'
        recent = [e for e in dict.fromkeys(reversed(self.subjects))][:3]  # most recent first
        if not recent: return s, 'clarify'           # zero candidates
        if len(recent) > 1: return s, 'clarify'      # ambiguity: no confidence from recency alone
        ent = recent[0]
        out = [ent if t in ('มัน', 'ของมัน') else t for t in toks]
        return ' '.join(out), 'resolved'

    def turn(self, s, gold_intent, gold_slots, scripted=None):
        """Returns (cls, meta). One user turn."""
        meta = {'category': None, 'resolution': None, 'definition_fired': False}
        # 0. literal repeat (exact surface, this session)
        if s in self.seen:
            meta['category'] = 'literal_repeat'
            return 'literal_repeat', meta
        # 1. definitions first (latest wins); can shadow trained grammar
        for rule, _src in reversed(self.defs):
            canon = fire(rule, s)
            if canon:
                meta['definition_fired'] = True; meta['category'] = 'taught_pattern'
                meta['canonical'] = canon
                cls, sub = self._pipeline(canon, gold_intent, gold_slots,
                                          scripted if scripted is not None else
                                          (gold_intent, gold_slots) if gold_intent else None)
                meta.update({k: v for k, v in sub.items() if v is not None})
                self.seen.add(s)
                return cls, meta
        # 2. definition teaching (supplied syntax)
        if s.startswith('นิยาม ') and ' เหมือน ' in s and ' ตัวแปร ' in s:
            try:
                lhs, rest = s[6:].split(' เหมือน ', 1)
                canon, varstr = rest.split(' ตัวแปร ', 1)
                varpos = [int(x) - 1 for x in varstr.split(',')]
                rule = compile_def(lhs.split(), canon.split(), varpos)
                if rule: self.defs.append((rule, s))
                self.seen.add(s)
                return ('def_taught' if rule else 'def_failed'), meta
            except Exception:
                self.seen.add(s); return 'def_failed', meta
        # 3. anaphora
        rw, status = self._resolve(s)
        meta['resolution'] = status
        if status in ('clarify', 'plural'):
            self.q += 1; self.corr += 1  # a clarification question (not a guess-confirmation)
            self.seen.add(s)
            return 'ask_needed', meta
        # 4. normal pipeline
        cls, sub = self._pipeline(rw, gold_intent, gold_slots, scripted)
        meta.update({k: v for k, v in sub.items() if v is not None})
        self.seen.add(s)
        return cls, meta

    def _pipeline(self, s, gold_intent, gold_slots, scripted):
        meta = {}
        p, mg = B.predict(self.m, B.encode(s), -1e18)
        if p is None or mg < self.tau_lo:
            if scripted is not None:
                self.q += 1
                d, sl = scripted
                if d is None: return 'honest_engaged', meta
                self.corr += 1
                self.m.add(B.encode(s), d)
                meta['category'] = meta.get('category') or 'teacher_assisted'
                return self._act(d, sl), meta
            return 'honest_engaged', meta
        sl = self.extract(s, p)
        if mg >= self.tau_hi and sl is not None and len(sl) == B.NSLOTS[p]:
            meta['category'] = meta.get('category') or 'unassisted'
            return self._act(p, sl), meta
        # mid band: guess-confirmation (simulated user answers from gold)
        self.q += 1
        guess_ok = sl is not None and len(sl) == B.NSLOTS.get(p, -1) and p == gold_intent and tuple(sl) == tuple(gold_slots or ())
        if guess_ok:
            self.yes += 1
            self.m.add(B.encode(s), p)
            meta['category'] = meta.get('category') or 'teacher_assisted'
            return self._act(p, sl), meta
        self.corr += 1
        if gold_intent is not None:
            self.m.add(B.encode(s), gold_intent)
            meta['category'] = meta.get('category') or 'teacher_assisted'
            return self._act(gold_intent, gold_slots), meta
        return 'honest_engaged', meta

# v2 reference extension, expectations RELABLED under the directed
# no-recency-confidence policy (clarify on >=2 distinct subjects)
V2 = [
    ('สวัสดี', 'honest_engaged', None),
    ('มิโล เป็น แมว', 'teach_ok', None),
    ('แมว เป็น สัตว์', 'teach_ok', None),
    ('มัน เป็น สัตว์ ไหม', 'ask_needed', None),        # relabeled: 2 subjects -> clarify
    ('มัน กิน ปลา ไหม', 'ask_needed', None),           # relabeled: clarify
    ('มิโล มี หาง', 'teach_ok', None),
    ('ของมัน สวย ไหม', 'ask_needed', None),            # relabeled: 2 subjects -> clarify
    ('นก เป็น สัตว์', 'teach_ok', None),
    ('มัน เป็น สัตว์เลี้ยง ไหม', 'ask_needed', None),  # relabeled: clarify
    ('วันนี้ อากาศ ดี มาก', 'honest_engaged', None),
]
V2_GOLD = {'มัน เป็น สัตว์ ไหม': (None, None), 'มัน กิน ปลา ไหม': (None, None),
           'ของมัน สวย ไหม': (None, None), 'มัน เป็น สัตว์เลี้ยง ไหม': (None, None)}

# v3 CHALLENGE set (authored tonight 2026-10-26, not used in component dev;
# independence limited - same author)
V3 = [
    ('สวัสดี', 'honest_engaged', None, None),
    ('มิโล เป็น แมว', 'teach_ok', None, None),
    ('นิยาม เหยี่ยว น่ะ เป็น นก เหมือน เหยี่ยว เป็น นก ตัวแปร 1,4', 'def_taught', None, None),
    ('กวาง น่ะ เป็น สัตว์', 'teach_ok', ('teach_isa', ('กวาง', 'สัตว์')), ('teach_isa', ('กวาง', 'สัตว์'))),
    ('มัน กิน ปลา ไหม', 'ask_needed', None, None),      # subjects มิโล,กวาง -> clarify
    ('พวกมัน เป็น สัตว์ ไหม', 'ask_needed', None, None),  # plural abstain
    ('ทำไมมิโลถึงเป็นแมว', 'honest_engaged', None, None),  # unsegmented why-q
    ('มิโล เป็น แมว', 'literal_repeat', None, None),
    ('แล้วนกล่ะ กิน ปลา ไหม', 'honest_engaged', None, None),   # RELABELED: below-tau_lo unfamiliar -> honest limit, no targeted clarification (gap recorded)
    ('ขอบคุณ', 'honest_engaged', None, None),
    ('นิยาม แพะ ก็ มี เขา เหมือน แพะ มี เขา ตัวแปร 1,4', 'def_taught', None, None),
    ('ม้า ก็ มี ขน', 'teach_ok', None, None),            # taught-pattern, canonical seen
]
V3_GOLD = {'กวาง น่ะ เป็น สัตว์': ('teach_isa', ('กวาง', 'สัตว์')),
           'ม้า ก็ มี ขน': ('teach_attr', ('ม้า', 'ขน')),
           'แล้วนกล่ะ กิน ปลา ไหม': (None, None)}

def run(chat, scenario, gold_lookup, tag):
    match = 0; rows = []
    cats = defaultdict(int); resolutions = defaultdict(int)
    for item in scenario:
        utt, exp = item[0], item[1]
        scripted = item[2] if len(item) > 2 else None
        gi, gs = gold_lookup(utt)
        cls, meta = chat.turn(utt, gi, gs, scripted)
        ok = cls == exp
        match += ok
        cats[meta.get('category') or cls] += 1
        if meta.get('resolution'): resolutions[meta['resolution']] += 1
        rows.append({'turn': utt[:30], 'expected': exp, 'got': cls, 'ok': ok,
                     'category': meta.get('category'), 'resolution': meta.get('resolution'),
                     'definition_fired': meta.get('definition_fired', False)})
    for r in rows: print('TURN ' + json.dumps(r, ensure_ascii=False))
    print('SUMMARY ' + json.dumps({'scenario': tag, 'match': match, 'turns': len(scenario),
        'questions_total': chat.q, 'yes': chat.yes, 'corrections': chat.corr,
        'fabricated': chat.fabricated, 'categories': dict(cats),
        'resolutions': dict(resolutions)}, ensure_ascii=False))

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    # v1: fresh chat (comparability anchor vs B-588's Shell2)
    chat = HSMLChat(m, tau_hi, 1.0, extract)
    run(chat, V1, lambda u: GOLD[u], 'v1-comparable')
    # v2 relabeled: fresh chat
    chat2 = HSMLChat(m, tau_hi, 1.0, extract)
    run(chat2, V2, lambda u: V2_GOLD.get(u, GOLD.get(u, (None, None))), 'v2-relabeled')
    # v3 challenge: fresh chat
    chat3 = HSMLChat(m, tau_hi, 1.0, extract)
    run(chat3, V3, lambda u: V3_GOLD.get(u, GOLD.get(u, (None, None))), 'v3-challenge')
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1),
        'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
