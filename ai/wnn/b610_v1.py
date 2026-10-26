"""B-610: learned first-guess discrimination, measurable scope and the
identifiability boundary. EVALUATION-ONLY subclass arms; hsml_chat.py
entry behavior untouched. Pre-registered (+amendment) in LEDGER.md
B-610. Usage: python3 b610.py"""
import json, sys, os
from collections import Counter
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b574 import pick_tau_precision
from b604 import learn_gold_stats, slot_offsets
from hsml_chat import InteractiveChat, RESTATE, QMARKERS, QINTENTS, MUTATING

class EvalChat(InteractiveChat):
    def __init__(self, *a, restrict_first=True, ctx=False, clarify_unsure=False, **kw):
        super().__init__(*a, **kw)
        self.restrict_first = restrict_first
        self.ctx = ctx
        self.clarify_unsure = clarify_unsure
        self._last_unknown = set()
        self._clarify_pending = None

    def _enc(self, s):
        f = Counter(super()._enc(s))
        if self.ctx and self._after_unknown(s):
            f['ctx:afterunk'] += 1
        return f

    def _after_unknown(self, s):
        if not self._last_unknown: return False
        return any(t in self._last_unknown for t in s.split() if t not in self.grammar)

    def _try_confirm(self, s, exclude=()):
        if self.restrict_first:
            return super()._try_confirm(s, exclude)
        for d, _sc in self._ranked(s):
            if d in exclude or d not in RESTATE: continue
            sl = self._extract(s, d)
            if sl is None or len(sl) != B.NSLOTS[d]: continue
            if self._unparsed(s, sl): continue
            if self._known(sl) or any(t in self.markers for t in s.split()):
                return d, sl
        return None, None

    def _handle_classified(self, s, via=None):
        if self.clarify_unsure and via is None:
            q = any(t in QMARKERS for t in s.split())
            if not q:
                p, mg = B.predict(self.m, self._enc(s), -1e18)
                if p in (QINTENTS | MUTATING) and mg < self.tau_lo:
                    sl_q = self._extract(s, 'is_a_q')
                    sl_t = self._extract(s, 'teach_isa')
                    if sl_q and sl_t:
                        self._clarify_pending = (s, sl_t, sl_q)
                        return 'ask_needed', 'ถามหรือสอน?', 'teacher_assisted'
        return super()._handle_classified(s, via)

    def user_turn(self, text):
        if self._clarify_pending is not None:
            s, sl_t, sl_q = self._clarify_pending
            if text == 'ถาม':
                self._clarify_pending = None
                return self._ask('confirm', surface=s, intent='is_a_q',
                                 slots=tuple(sl_q), rejected=['is_a_q'])
            if text == 'สอน':
                self._clarify_pending = None
                return self._ask('confirm', surface=s, intent='teach_isa',
                                 slots=tuple(sl_t), rejected=['teach_isa'])
        self._last_unknown = set()
        r = super().user_turn(text)
        if r.startswith('ไม่รู้ว่า'):
            skip = {'ไม่รู้ว่า', 'ยังไม่เคยถูกสอน'} | self.grammar
            self._last_unknown = {self._clean(t) for t in r.split() if t not in skip}
        return r

def make(**kw):
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    frame, fillers, vocab = learn_gold_stats(train)
    soff = slot_offsets(train, anchor0)
    return EvalChat(m, tau_hi, 1.0, frame, fillers, soff, fn0, anchor0,
                    offstat0, rolepos0, vocab, **kw)

DERANGE = {'is_a_q': 'teach_isa', 'teach_isa': 'is_a_q',
           'ask_attr': 'teach_attr', 'teach_attr': 'ask_attr'}

def classify_guess(r):
    if r.startswith('ถามหรือสอน?'): return 'clarify'
    if 'เดาว่า: ถามว่า' in r: return 'q'
    if 'เดาว่า: สอนว่า' in r: return 'stmt'
    if r.startswith('ไม่รู้ว่า') or r.startswith('ใช่ ') or r.startswith('รู้ว่า'): return 'q'
    if r.startswith('จำแล้ว'): return 'stmt'
    return 'other:' + r[:30]

def drive(c, surface, gold, max_turns=5):
    r = c.user_turn(surface)
    first = classify_guess(r)
    turns = 0
    if first == 'q' and not r.startswith('เดาว่า'):
        return first, 0, gold == 'q', gold != 'q'      # unassisted answer
    if first == 'stmt' and not r.startswith('เดาว่า') and 'ตามรูปแบบ' not in r:
        return first, 0, gold == 'stmt', gold != 'stmt'  # unassisted commit
    while turns < max_turns:
        if 'ถามว่า' in r[:70]:
            fb = 'ใช่' if gold == 'q' else 'ไม่ใช่'
        elif 'สอนว่า' in r[:70]:
            fb = 'ใช่' if gold == 'stmt' else 'ไม่ใช่'
        elif r.startswith('ถามหรือสอน?'):
            fb = 'ถาม' if gold == 'q' else 'สอน'
        else:
            return first, turns, False, False
        r = c.user_turn(fb); turns += 1
        if fb == 'ใช่':
            return first, turns, True, False
    return first, turns, False, False

LEARN_CUED = [('ม้าเป็นสัตว์เลี้ยง', 'ม้าเป็นสัตว์เลี้ยงไหม'),
              ('แพะเป็นสัตว์เลี้ยง', 'แพะเป็นสัตว์เลี้ยงไหม'),
              ('ควายเป็นสัตว์ป่า', 'ควายเป็นสัตว์ป่าไหม'),
              ('เป็ดเป็นนก', 'เป็ดเป็นนกไหม')]
LEARN_Q = ['เสือเป็นสัตว์', 'หมูเป็นสัตว์เลี้ยง', 'ไก่เป็นนก',
           'แมวเป็นสัตว์', 'วัวเป็นนก', 'ช้างเป็นนก']
TEST = [('T1', 'ลิงเป็นสัตว์ป่า', 'stmt', 'ลิงเป็นสัตว์ป่าไหม', 'cued'),
        ('T2', 'กบเป็นสัตว์', 'stmt', 'กบเป็นสัตว์ไหม', 'cued'),
        ('T3', 'หมีเป็นสัตว์ป่า', 'stmt', None, 'uncued_stmt'),
        ('T4', 'แพนด้าเป็นสัตว์เลี้ยง', 'stmt', None, 'uncued_stmt'),
        ('T5', 'ม้าเป็นนก', 'q', None, 'uncued_q_AMBIGUOUS'),
        ('T6', 'เสือเป็นนก', 'q', None, 'uncued_q_AMBIGUOUS'),
        ('T7', 'มิโลมีหาง', 'q', None, 'heldout_structure_AMBIGUOUS'),
        ('T8', 'ลิงเป็นสัตว์ป่าไหม', 'q', None, 'marked_control')]

def run_arm(name, **kw):
    c = make(**kw)
    if kw.get('perm'):
        c._feedback_label = lambda d: DERANGE.get(d, d)
    for stmt, q in LEARN_CUED:
        c.user_turn(q)
        drive(c, stmt, 'stmt')
    for s in LEARN_Q:
        drive(c, s, 'q')
    rows = {}
    for tid, surface, gold, setup, cls in TEST:
        if setup: c.user_turn(setup)
        first, turns, success, wrong_un = drive(c, surface, gold)
        rows[tid] = {'cls': cls, 'gold': gold, 'first': first,
                     'turns': turns, 'success': success, 'wrong_unassisted': wrong_un}
    return rows

arms = {
    'BASE': dict(),
    'NORESTRICT': dict(restrict_first=False, ctx=True),
    'NCLAR': dict(restrict_first=False, ctx=True, clarify_unsure=True),
    'NOCORR': dict(restrict_first=False, ctx=True),
    'PERM': dict(restrict_first=False, ctx=True, perm=True),
}
out = {}
for name, kw in arms.items():
    rows = run_arm(name, **kw)
    if name == 'NOCORR':
        pass
    out[name] = rows
# NOCORR: disable feedback learning
c = make(restrict_first=False, ctx=True); c.learn_from_feedback = False
rows = {}
for stmt, q in LEARN_CUED:
    c.user_turn(q); drive(c, stmt, 'stmt')
for s in LEARN_Q: drive(c, s, 'q')
for tid, surface, gold, setup, cls in TEST:
    if setup: c.user_turn(setup)
    first, turns, success, wrong_un = drive(c, surface, gold)
    rows[tid] = {'cls': cls, 'gold': gold, 'first': first,
                 'turns': turns, 'success': success, 'wrong_unassisted': wrong_un}
out['NOCORR'] = rows

print('RESULTS ' + json.dumps(out, ensure_ascii=False))

def acc(rows, ids):
    return sum(1 for t in ids if rows[t]['first'] == rows[t]['gold']), len(ids)

base = out['BASE']
cued = ['T1', 'T2']; uncued_stmt = ['T3', 'T4']; ambig = ['T5', 'T6', 'T7']
gate = {}
gate['base_identifiable'] = acc(base, cued + uncued_stmt + ['T8'])
gate['base_ok'] = gate['base_identifiable'][0] == gate['base_identifiable'][1]
nr = out['NORESTRICT']; nc = out['NOCORR']; pm = out['PERM']; ncl = out['NCLAR']
gate['norestrict_cued'] = acc(nr, cued)
gate['norestrict_uncued_stmt_recall'] = acc(nr, uncued_stmt)[0]
gate['nocorr_cued'] = acc(nc, cued)
gate['nocorr_no_benefit'] = acc(nc, cued)[0] <= gate['base_identifiable'][0] and acc(nc, uncued_stmt)[0] >= acc(nr, uncued_stmt)[0]
gate['perm_cued_collapses'] = acc(pm, cued)[0] == 0
gate['nclar_burden_ambig'] = sum(ncl[t]['turns'] for t in uncued_stmt + ambig)
gate['base_burden_ambig'] = sum(base[t]['turns'] for t in uncued_stmt + ambig)
gate['norestrict_burden_ambig'] = sum(nr[t]['turns'] for t in uncued_stmt + ambig)
gate['nclar_no_wrong_unassisted'] = not any(ncl[t]['wrong_unassisted'] for t in TEST and [x[0] for x in TEST] for t in [x[0] for x in TEST])
gate['nclar_no_wrong_unassisted'] = not any(ncl[t]['wrong_unassisted'] for t in ncl)
gate['norestrict_wrong_unassisted'] = sum(1 for t in nr if nr[t]['wrong_unassisted'])
gate['all_final_success'] = {a: all(r['success'] for r in out[a].values()) for a in out}
ok = (gate['base_ok'] and gate['nocorr_no_benefit'] and gate['perm_cued_collapses']
      and gate['nclar_burden_ambig'] <= gate['base_burden_ambig']
      and gate['nclar_no_wrong_unassisted'])
print('GATE ' + json.dumps(gate, ensure_ascii=False, default=str))
print('CHECK PASS' if ok else 'CHECK FAIL')
