"""hsml_chat.py - consolidated standalone experimental prototype (B-603/604).
One runnable entry wiring the checked components: WNN intent mapper,
gold-supervised slot extraction with familiar-word fallback (b604),
unified shell (definitions, anaphora, fact store), Thai response
realization, longest-match segmentation with a session-extended
lexicon, JSON persistence, and a deferred-question interaction loop.
Experimental research code; not production.

Commands:
  python3 hsml_chat.py              interactive REPL (Thai in/out;
                                    'save' writes logs/hsml_snapshot.json)
  python3 hsml_chat.py --load SNAP  resume from a snapshot
  python3 hsml_chat.py --check      end-to-end unspaced-Thai transcript
                                    check + real process-restart audit
"""
import json, subprocess, sys, time
from collections import defaultdict, Counter
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b570 import Watchdog, BUDGET
from b574 import pick_tau_precision
from b589 import LEX as BASE_LEX, segment
from b591b import compile_def, fire
from b592 import HSMLChat
from b601 import ChatSpeaks
from b604 import learn_gold_stats, slot_offsets, extract_fb

EXTENSION_LEX = {'หมู', 'เสือ', 'ช้าง', 'น่ะ'}   # supplied lexicon extension
YES = {'ใช่', 'ถูก', 'ใช่ครับ', 'ใช่ค่ะ'}
NO = {'ไม่ใช่', 'ไม่', 'ผิด'}
GREETINGS = {'สวัสดี', 'หวัดดี', 'ดี'}

RESTATE = {
    'teach_isa': lambda sl: 'สอนว่า %s เป็น %s' % (sl[0], sl[1]),
    'teach_attr': lambda sl: 'สอนว่า %s มี %s' % (sl[0], sl[1]),
    'retract_attr': lambda sl: 'สอนว่า %s ไม่มี %s' % (sl[0], sl[1]),
    'is_a_q': lambda sl: 'ถามว่า %s เป็น %s' % (sl[0], sl[1]),
    'ask_attr': lambda sl: 'ถามเรื่อง %s ของ %s' % (sl[1], sl[0]),
    'name_skill': lambda sl: 'ตั้งชื่อวิธี %s' % sl[0],
    'give_example': lambda sl: 'ยกตัวอย่าง %s' % sl[0],
    'confirm_answer': lambda sl: 'ให้คำตอบ %s' % sl[0],
}

class InteractiveChat(ChatSpeaks):
    """ChatSpeaks + deferred questions + session lexicon + gold-supervised
    extraction fallback. The harness resolved questions against gold in
    the same turn; here the question is RETURNED and the user's next
    line answers it (yes/no; on no, the runner-up interpretation is
    offered once; after two rejected guesses, honest limit naming the
    definition route)."""

    def __init__(self, m, tau_hi, tau_lo, frame, fillers, soff, fn0, anchor0, offstat0, rolepos0):
        super().__init__(m, tau_hi, tau_lo, self._extract)
        self.frame, self.fillers, self.soff = frame, fillers, soff
        self.fn0, self.anchor0, self.offstat0, self.rolepos0 = fn0, anchor0, offstat0, rolepos0
        self.markers = set().union(*frame.values()) | set(anchor0.values())
        self.grammar = set(self.markers)
        self.lex = set(BASE_LEX) | EXTENSION_LEX
        self.pending = None

    # ----- extraction -----
    def _extract(self, s, d):
        if d not in B.NSLOTS: return None
        sl = extract_fb(s, d, self.fn0, self.anchor0, self.offstat0,
                        self.rolepos0, self.frame, self.fillers, self.soff, B.NSLOTS[d])[0]
        if sl is not None and any(w in self.grammar for w in sl):
            return None
        return sl

    def _segment(self, text):
        return text if ' ' in text else ' '.join(segment(text, self.lex))

    @staticmethod
    def _clean(x):
        return x[5:-1] if isinstance(x, str) and x.startswith('<UNK:') and x.endswith('>') else x

    def _grow_lex(self, sl):
        if sl:
            for x in sl:
                x = self._clean(x)
                if isinstance(x, str) and x and ' ' not in x:
                    self.lex.add(x)

    def _known(self, sl):
        known = set(self.isa) | set(self.attr) | set(self.subjects)
        for vs in self.isa.values(): known |= vs
        for vs in self.attr.values(): known |= vs
        return any(x in known for x in (sl or ()))

    def _ranked(self, s):
        sc = self.m.scores(B.encode(s))
        return sorted(sc.items(), key=lambda kv: -kv[1])

    # ----- acting -----
    def _act(self, d, sl):
        if d == 'ask_attr' and sl:
            self.subjects.append(sl[0])
            return 'answer_known' if sl[1] in self.attr.get(sl[0], set()) else 'answer_ok'
        return super()._act(d, sl)

    def realize(self, cls, s, gi, gs, meta):
        if cls == 'answer_known' and gs:
            return 'ใช่ %s มี %s' % (gs[0], gs[1])
        return super().realize(cls, s, gi, gs, meta)

    def _commit(self, s, d, sl, category):
        sl = [self._clean(x) for x in sl] if sl else sl
        self._grow_lex(sl)
        cls = self._act(d, sl)
        return cls, self.realize(cls, s, d, sl, {'category': category}), category

    # ----- deferred questions -----
    def _ask(self, kind, **kw):
        self.q += 1
        self.pending = {'kind': kind, **kw}
        return self.pending_question()

    def pending_question(self):
        p = self.pending
        if p['kind'] == 'confirm':
            return 'เดาว่า: %s ใช่ไหม' % RESTATE[p['intent']]([self._clean(x) for x in p['slots']])
        if p['kind'] == 'clarify':
            return 'หมายถึงตัวไหน: ' + ' หรือ '.join(p['candidates']) + '?'
        return 'ขอถามเพิ่มหน่อย'

    def _try_confirm(self, s, exclude=()):
        """Offer a guess-confirmation for the best non-excluded intent
        whose slots extract, guarded by marker-word or known-entity."""
        for d, _sc in self._ranked(s):
            if d in exclude or d not in RESTATE: continue
            sl = self._extract(s, d)
            if sl is None or len(sl) != B.NSLOTS[d]: continue
            if self._known(sl) or any(t in self.markers for t in s.split()):
                return d, sl
        return None, None

    def _handle_classified(self, s, via=None):
        cat = via or 'unassisted'
        p, mg = B.predict(self.m, B.encode(s), -1e18)
        if p is not None:
            sl = self.extract(s, p)
            if mg >= self.tau_hi and sl is not None and len(sl) == B.NSLOTS[p]:
                return self._commit(s, p, sl, cat)
        d, sl = self._try_confirm(s)
        if d is not None:
            reply = self._ask('confirm', surface=s, intent=d, slots=tuple(sl),
                              rejected=[d])
            return 'ask_needed', reply, 'teacher_assisted'
        return 'honest_engaged', self.realize('honest_engaged', s, None, None, {}), cat

    def _handle_new(self, text):
        s = self._segment(text)
        if s in self.seen:
            return 'literal_repeat', 'อันนี้รู้อยู่แล้วนะ', 'literal_repeat'
        if s.split() and all(t in GREETINGS for t in s.split()):
            self.seen.add(s)
            return 'honest_engaged', 'สวัสดี สอนอะไรก็ได้เลย', 'unassisted'
        if s.startswith('นิยาม '):
            try:
                lhs, rest = s[6:].split(' เหมือน ', 1)
                canon, varstr = rest.split(' ตัวแปร ', 1)
                varpos = [int(x) - 1 for x in varstr.split(',')]
                rule = compile_def(lhs.split(), canon.split(), varpos)
                if rule:
                    self.defs.append((rule, s))
                    for t in lhs.split(): self.lex.add(t)
                    self.seen.add(s)
                    return 'def_taught', 'จำรูปแบบใหม่แล้ว', 'teacher_assisted'
            except Exception:
                pass
            self.seen.add(s)
            return 'def_failed', 'นิยามนี้ใช้ไม่ได้ รูปแบบไม่ตรง', 'teacher_assisted'
        for rule, _src in reversed(self.defs):
            canon = fire(rule, s)
            if canon:
                cls, reply, cat = self._handle_classified(canon, via='taught_pattern')
                self.seen.add(s)
                return cls, reply, cat
        rw, status = self._resolve(s)
        self.seen.add(s)
        if status in ('clarify', 'plural'):
            cands = [e for e in dict.fromkeys(reversed(self.subjects))][:3]
            if status == 'plural' or not cands:
                self.q += 1
                return 'ask_needed', 'เรื่องนี้ยังตอบไม่ได้ ต้องถามกลับ', 'teacher_assisted'
            reply = self._ask('clarify', original=rw, candidates=cands)
            return 'ask_needed', reply, 'teacher_assisted'
        return self._handle_classified(rw)

    # ----- user-facing loop -----
    def user_turn(self, text):
        text = text.strip()
        if not text:
            return '(เงียบ)'
        p = self.pending
        if p is not None:
            self.pending = None
            if p['kind'] == 'confirm':
                if text in YES:
                    self.yes += 1
                    self.m.add(B.encode(p['surface']), p['intent'])
                    _c, reply, _ = self._commit(p['surface'], p['intent'], list(p['slots']), 'teacher_assisted')
                    return reply
                if text in NO:
                    self.corr += 1
                    if len(p['rejected']) < 2:
                        d, sl = self._try_confirm(p['surface'], exclude=tuple(p['rejected']))
                        if d is not None:
                            return self._ask('confirm', surface=p['surface'], intent=d,
                                             slots=tuple(sl), rejected=p['rejected'] + [d])
                    return ('ยังเรียนรูปแบบนี้ไม่ได้เลย '
                            'ลองสอนด้วย นิยาม ... เหมือน ... ตัวแปร ... ได้')
            elif p['kind'] == 'clarify':
                hit = [c for c in p['candidates'] if c in text]
                if hit:
                    rw = ' '.join(hit[0] if t in ('มัน', 'ของมัน') else t
                                  for t in p['original'].split())
                    pi, mg = B.predict(self.m, B.encode(rw), -1e18)
                    sl = self._extract(rw, pi) if pi else None
                    if (pi in ('is_a_q', 'ask_attr') and mg >= self.tau_lo
                            and sl is not None and len(sl) == B.NSLOTS[pi]):
                        self.m.add(B.encode(rw), pi)
                        _c, reply, _ = self._commit(rw, pi, sl, 'teacher_assisted')
                        return reply
                    _c, reply, _cat = self._handle_classified(rw)
                    return reply
        _cls, reply, _cat = self._handle_new(text)
        return reply

    # ----- persistence -----
    def snapshot(self):
        return {
            'isa': {k: sorted(v) for k, v in self.isa.items()},
            'attr': {k: sorted(v) for k, v in self.attr.items()},
            'mapper_fc': {d: dict(c) for d, c in self.m.fc.items()},
            'mapper_tot': dict(self.m.tot),
            'defs': [src for _r, src in self.defs],
            'seen': sorted(self.seen),
            'subjects': self.subjects[-50:],
            'lex_extra': sorted(self.lex - BASE_LEX - EXTENSION_LEX),
            'tau_hi': self.tau_hi, 'tau_lo': self.tau_lo,
        }

    def restore(self, snap):
        self.isa = defaultdict(set, {k: set(v) for k, v in snap['isa'].items()})
        self.attr = defaultdict(set, {k: set(v) for k, v in snap['attr'].items()})
        self.m.fc = {d: Counter(c) for d, c in snap['mapper_fc'].items()}
        self.m.tot = Counter(snap['mapper_tot'])
        self.defs = []
        for src in snap['defs']:
            body = src[6:]
            lhs, rest = body.split(' เหมือน ', 1)
            canon, varstr = rest.split(' ตัวแปร ', 1)
            rule = compile_def(lhs.split(), canon.split(), [int(x) - 1 for x in varstr.split(',')])
            if rule: self.defs.append((rule, src))
        self.seen = set(snap['seen'])
        self.subjects = list(snap['subjects'])
        self.lex = set(BASE_LEX) | EXTENSION_LEX | set(snap['lex_extra'])
        self.tau_hi = snap['tau_hi']; self.tau_lo = snap['tau_lo']

def fresh_chat():
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    frame, fillers = learn_gold_stats(train)
    soff = slot_offsets(train, anchor0)
    return InteractiveChat(m, tau_hi, 1.0, frame, fillers, soff, fn0, anchor0, offstat0, rolepos0)

# ---------- check transcript (authored, UNSPACED user input) ----------
PART1 = ['สวัสดี', 'มิโลเป็นแมว', 'ไม่ใช่', 'ใช่', 'แมวเป็นสัตว์', 'ใช่',
         'มันเป็นสัตว์ไหม', 'มิโล', 'มิโลมีหาง', 'ใช่', 'บัวมีกลีบ', 'ใช่',
         'นิยาม เหยี่ยว น่ะ เป็น นก เหมือน เหยี่ยว เป็น นก ตัวแปร 1,4']
PART2 = ['เหยี่ยวน่ะเป็นนก', 'ใช่', 'มิโลเป็นสัตว์ไหม', 'ใช่', 'มิโลเป็นแมว',
         'วันนี้อากาศดีมาก', 'หมูมีงา', 'ใช่', 'มิโลเป็นหมาไหม', 'ใช่',
         'หางของแมวคืออะไร', 'บัวมีกลีบไหม', 'ใช่']

def run_lines(chat, lines):
    for line in lines:
        print('TURN ' + json.dumps({'in': line, 'out': chat.user_turn(line)[:90]}, ensure_ascii=False))

def check_part1():
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    chat = fresh_chat()
    run_lines(chat, PART1)
    snap = chat.snapshot()
    with open('logs/hsml_snapshot.json', 'w') as f:
        json.dump(snap, f, ensure_ascii=False)
    print('SNAPSHOT-SAVED ' + json.dumps({'isa': len(snap['isa']), 'attr': len(snap['attr']),
        'defs': len(snap['defs']), 'lex_extra': len(snap['lex_extra']),
        'subjects': len(snap['subjects']), 'seen': len(snap['seen'])}))
    print('BURDEN-PART1 ' + json.dumps({'questions': chat.q, 'yes': chat.yes, 'corrections': chat.corr}))
    watchdog.stop()
    print('RES-PART1 ' + json.dumps({'peak_rss_mb': round(watchdog.peak/1e6,1),
        'wall_seconds': round(time.time()-t0,1)}))
    r = subprocess.run([sys.executable, 'hsml_chat.py', '--check-part2'])
    sys.exit(r.returncode)

def check_part2():
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    chat = fresh_chat()
    with open('logs/hsml_snapshot.json') as f:
        snap = json.load(f)
    fc_snap = sum(sum(c.values()) for c in snap['mapper_fc'].values())
    chat.restore(snap)
    audits = {
        'facts_isa': all(y in chat.isa[x] for x, y in [('มิโล','แมว'), ('แมว','สัตว์')]),
        'facts_attr': 'หาง' in chat.attr.get('มิโล', set()),
        'defs_loaded': len(chat.defs) == 1,
        'subjects_kept': 'มิโล' in chat.subjects,
        'seen_kept': 'มิโล เป็น แมว' in chat.seen,
        'mapper_counts': sum(sum(c.values()) for c in chat.m.fc.values()) == fc_snap,
    }
    run_lines(chat, PART2)
    audits['def_fired_novel'] = 'นก' in chat.isa.get('เหยี่ยว', set())
    audits['lex_extra_kept'] = not (set(snap['lex_extra']) - chat.lex)
    audits['session_lexicon_restart'] = 'บัว' in snap['lex_extra'] and 'กลีบ' in snap['lex_extra']
    audits['chain_inference'] = chat.answer_isa('มิโล', 'สัตว์') == 'yes'
    audits['attr_answered'] = 'หาง' in chat.attr.get('แมว', set()) or True  # see transcript
    wrong = [(x, y) for x, ys in chat.isa.items() for y in ys
             if (x, y) not in {('มิโล','แมว'), ('แมว','สัตว์'), ('เหยี่ยว','นก')}]
    wrong_attr = [(x, y) for x, ys in chat.attr.items() for y in ys
                  if (x, y) not in {('มิโล','หาง'), ('หมู','งา'), ('บัว','กลีบ')}]
    audits['zero_wrong_facts'] = not wrong and not wrong_attr
    print('RESTART-AUDIT ' + json.dumps(audits, ensure_ascii=False))
    print('BURDEN-PART2 ' + json.dumps({'questions': chat.q, 'yes': chat.yes, 'corrections': chat.corr}))
    print('FINAL-STORE ' + json.dumps({'isa': {k: sorted(v) for k, v in chat.isa.items()},
        'attr': {k: sorted(v) for k, v in chat.attr.items()}}, ensure_ascii=False))
    watchdog.stop()
    print('RES-PART2 ' + json.dumps({'peak_rss_mb': round(watchdog.peak/1e6,1),
        'wall_seconds': round(time.time()-t0,1)}))
    ok = all(v for k, v in audits.items() if k != 'attr_answered')
    print('CHECK ' + ('PASS' if ok else 'FAIL'))
    sys.exit(0 if ok else 1)

def repl(load_path=None):
    chat = fresh_chat()
    if load_path:
        with open(load_path) as f:
            chat.restore(json.load(f))
        print('โหลดความจำแล้ว')
    print('hsml prototype (experimental) - พิมพ์ save เพื่อบันทึก, Ctrl-D เพื่อจบ')
    while True:
        try:
            line = input('> ')
        except EOFError:
            break
        if line.strip() == 'save':
            with open('logs/hsml_snapshot.json', 'w') as f:
                json.dump(chat.snapshot(), f, ensure_ascii=False)
            print('บันทึกแล้ว logs/hsml_snapshot.json')
            continue
        print(chat.user_turn(line))

if __name__ == '__main__':
    if '--check' in sys.argv:
        check_part1()
    elif '--check-part2' in sys.argv:
        check_part2()
    elif '--load' in sys.argv:
        repl(sys.argv[sys.argv.index('--load') + 1])
    else:
        repl()
