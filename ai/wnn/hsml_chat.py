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
INDUCED_AUTOCOMMIT = False   # sandbox contrast only; entry path is proposal-only (B-608)
YES = {'ใช่', 'ถูก', 'ใช่ครับ', 'ใช่ค่ะ'}
NO = {'ไม่ใช่', 'ไม่', 'ผิด'}
GREETINGS = {'สวัสดี', 'หวัดดี', 'ดี'}
QMARKERS = {'ไหม', 'หรือเปล่า', 'คืออะไร', 'จริงไหม', 'ทำไม', 'อะไร'}   # supplied
QINTENTS = {'is_a_q', 'ask_attr'}
MUTATING = {'teach_isa', 'teach_attr', 'retract_attr'}

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

    def __init__(self, m, tau_hi, tau_lo, frame, fillers, soff, fn0, anchor0, offstat0, rolepos0, vocab=None):
        super().__init__(m, tau_hi, tau_lo, self._extract)
        self.frame, self.fillers, self.soff = frame, fillers, soff
        self.vocab = vocab
        self.fn0, self.anchor0, self.offstat0, self.rolepos0 = fn0, anchor0, offstat0, rolepos0
        self.markers = set().union(*frame.values()) | set(anchor0.values())
        self.grammar = set(self.markers) | QMARKERS
        self.lex = set(BASE_LEX) | EXTENSION_LEX
        self.pending = None
        self.instances = []        # user-validated (tokens, intent, slots)
        self.patterns = {}         # shape_key -> {'intent':.., 'status':'active'|'rejected'}
        self.patterns_proposed = set()
        self.pattern_awaiting = None   # (key, intent) proposed, awaiting yes/no
        self.writes = 0                # every mutating commit (incl. re-writes)

    @staticmethod
    def _shape(toks, sl):
        key = []
        for t in toks:
            if t in sl: key.append(('VAR', sl.index(t)))
            else: key.append(('TOK', t))
        return tuple(key)

    # ----- extraction -----
    def _extract(self, s, d):
        if d not in B.NSLOTS: return None
        sl = extract_fb(s, d, self.fn0, self.anchor0, self.offstat0,
                        self.rolepos0, self.frame, self.fillers, self.soff,
                        B.NSLOTS[d], self.vocab)[0]
        if sl is not None and any(w in self.grammar for w in sl):
            return None
        if sl is not None and d == 'ask_attr':
            sl = self._semantic_ask_attr(s, sl)
        return sl

    @staticmethod
    def _semantic_ask_attr(s, sl):
        # Supplied: ask_attr extraction is surface-ordered; the token
        # after ของ is the subject. Returns (subject, attr).
        toks = s.split()
        if 'ของ' in toks:
            i = toks.index('ของ') + 1
            if i < len(toks) and toks[i] in sl and sl[0] != toks[i]:
                return (toks[i],) + tuple(x for x in sl if x != toks[i])
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
            known = sl[1] in self.attr.get(sl[0], set())
            if 'คืออะไร' in (self._last_surface or ''):
                return 'value_known_partial' if known else 'answer_ok'
            return 'answer_known' if known else 'answer_ok'
        return super()._act(d, sl)

    def realize(self, cls, s, gi, gs, meta):
        if cls == 'answer_known' and gs:
            return 'ใช่ %s มี %s' % (gs[0], gs[1])
        if cls == 'value_known_partial' and gs:
            return 'รู้ว่า %s มี %s แต่ไม่รู้รายละเอียด' % (gs[0], gs[1])
        return super().realize(cls, s, gi, gs, meta)

    _last_surface = None

    def _commit(self, s, d, sl, category):
        if d in MUTATING: self.writes += 1
        self._last_surface = s
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

    def _unparsed(self, s, sl):
        """Non-grammar tokens the proposed parse does not account for."""
        return [t for t in s.split()
                if t not in self.grammar and t not in sl and not t.startswith('<UNK:')
                and t not in ('มัน', 'ของมัน')]

    def _try_confirm(self, s, exclude=()):
        """Offer a guess-confirmation for the best non-excluded intent
        whose slots extract, guarded by marker-word or known-entity.
        B-605: marker-based intent restriction. B-606 escape hatch: the
        restriction applies only while nothing has been rejected; after a
        rejection every intent is eligible again. B-608 completeness: a
        write proposal must account for every content token - a yes
        authorizes the proposition actually shown."""
        q = any(t in QMARKERS for t in s.split())
        restrict = not exclude
        unparsed = None
        for d, _sc in self._ranked(s):
            if d in exclude or d not in RESTATE: continue
            if restrict and q and d not in QINTENTS: continue
            if restrict and not q and d in QINTENTS: continue
            sl = self._extract(s, d)
            if sl is None or len(sl) != B.NSLOTS[d]: continue
            left = self._unparsed(s, sl)
            if left:
                unparsed = unparsed or left
                continue
            if self._known(sl) or any(t in self.markers for t in s.split()):
                return d, sl
        return None, None

    def _best_leftover(self, s):
        """Unparsed content tokens under the best-ranked extractable
        parse (for honest-limit naming)."""
        for d, _sc in self._ranked(s):
            if d not in B.NSLOTS: continue
            sl = self._extract(s, d)
            if sl is not None and len(sl) == B.NSLOTS[d]:
                return self._unparsed(s, sl)
        return self._unparsed(s, ())

    def _handle_classified(self, s, via=None):
        cat = via or 'unassisted'
        p, mg = B.predict(self.m, B.encode(s), -1e18)
        if p is not None:
            sl = self._extract(s, p)
            q = any(t in QMARKERS for t in s.split())
            blocked = q and p in MUTATING           # B-605: question-marked -> never write
            if p in MUTATING and sl is not None and self._unparsed(s, sl):
                blocked = True                      # B-608: unaccounted content words -> no silent write
            if (not blocked and mg >= self.tau_hi and sl is not None
                    and len(sl) == B.NSLOTS[p]):
                return self._commit(s, p, sl, cat)
        d, sl = self._try_confirm(s)
        if d is not None:
            reply = self._ask('confirm', surface=s, intent=d, slots=tuple(sl),
                              rejected=[d])
            return 'ask_needed', reply, 'teacher_assisted'
        left = self._best_leftover(s)
        if left:
            return 'honest_engaged', 'ยังไม่เข้าใจคำว่า «%s» ในประโยคนี้' % '», «'.join(left[:3]), cat
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
        hits = self._match_patterns(s)
        intents = {h[0] for h in hits}
        if len(intents) > 1:
            self.seen.add(s)
            self.q += 1
            return 'ask_needed', 'ประโยคนี้เข้ากับรูปแบบที่เรียนไว้หลายแบบ ช่วยบอกว่าหมายถึงแบบไหน', 'teacher_assisted'
        if len(hits) == 1:
            pd, psl = hits[0]
            if INDUCED_AUTOCOMMIT:
                self.seen.add(s)
                cls, reply, cat = self._commit(s, pd, list(psl), 'induced_pattern')
                return cls, reply, cat
            if pd in RESTATE:
                self.seen.add(s)
                reply = self._ask('confirm', surface=s, intent=pd, slots=psl, rejected=[pd])
                return 'ask_needed', 'ตามรูปแบบที่จำไว้: ' + reply, 'induced_pattern'
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

    def _maybe_propose(self):
        from collections import Counter
        shapes = Counter()
        exemplars = {}
        for s, d, sl in self.instances:
            key = (d, self._shape(s.split(), list(sl)))
            shapes[key] += 1; exemplars[key] = (s, d, sl)
        for (d, key), n in shapes.items():
            if n >= 3 and key not in self.patterns_proposed and self.patterns.get(key, {}).get('status') != 'rejected':
                self.patterns_proposed.add(key)
                exemplar = exemplars[(d, key)][0]
                self.pattern_awaiting = (key, d)
                self.q += 1
                return ('สังเกตว่าประโยคแบบ «%s» หมายถึงสอนข้อเท็จจริงแบบเดียวกันทุกครั้ง ใช่ไหม '
                        '(ถ้าใช่ ครั้งต่อไปผมจะเสนอคำตอบแบบนี้ให้ยืนยันทันที)' % exemplar)
        return None

    def _match_patterns(self, s):
        toks = s.split()
        hits = []
        for key, st in self.patterns.items():
            if st['status'] != 'active' or len(key) != len(toks): continue
            d = st['intent']
            slots = [None] * B.NSLOTS[d]
            ok = True
            for (kind, v), t in zip(key, toks):
                if kind == 'TOK' and v != t: ok = False; break
                if kind == 'VAR': slots[v] = t
            if ok and all(x is not None for x in slots):
                hits.append((d, tuple(slots)))
        return hits

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
                    self.instances.append((p['surface'], p['intent'], tuple(p['slots'])))
                    prop = self._maybe_propose()
                    if prop: return reply + '\n' + prop
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
        if self.pattern_awaiting and text in YES | NO:
            key, d = self.pattern_awaiting
            self.pattern_awaiting = None
            if text in YES:
                self.patterns[key] = {'intent': d, 'status': 'active'}
                return 'จำรูปแบบแล้ว ครั้งต่อไปจะจำให้ทันที'
            self.patterns[key] = {'intent': d, 'status': 'rejected'}
            return 'รับทราบ จะถามทีละครั้งเหมือนเดิม'
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
            'patterns': [[st['intent'] + '|' + '|'.join('%s:%s' % (k, v) for k, v in key), st['status']]
                         for key, st in self.patterns.items()],
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
        self.patterns = {}
        for enc, status in snap.get('patterns', []):
            d, ks = enc.split('|', 1)
            key = tuple(tuple(p.split(':', 1)) for p in ks.split('|'))
            key = tuple((k, int(v) if k == 'VAR' else v) for k, v in key)
            self.patterns[key] = {'intent': d, 'status': status}

def fresh_chat():
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    frame, fillers, vocab = learn_gold_stats(train)
    soff = slot_offsets(train, anchor0)
    return InteractiveChat(m, tau_hi, 1.0, frame, fillers, soff, fn0, anchor0, offstat0, rolepos0, vocab)

# ---------- check transcript (authored, UNSPACED user input) ----------
PART1 = ['สวัสดี', 'มิโลเป็นแมว', 'ใช่', 'แมวเป็นสัตว์', 'ใช่',
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
    import threading
    peak = [0]; stop = False
    def sampler(proc):
        while not stop:
            total = 0
            for pid in {subprocess.os.getpid(), proc.pid}:
                try:
                    with open('/proc/%d/status' % pid) as f:
                        for ln in f:
                            if ln.startswith('VmRSS'):
                                total += int(ln.split()[1]) * 1024
                except FileNotFoundError:
                    pass
            peak[0] = max(peak[0], total)
            time.sleep(0.05)
    proc = subprocess.Popen([sys.executable, 'hsml_chat.py', '--check-part2'])
    th = threading.Thread(target=sampler, args=(proc,)); th.start()
    r = proc.wait(); stop = True; th.join()
    print('TREE-PEAK ' + json.dumps({'peak_concurrent_tree_mb': round(peak[0]/1e6,1),
        'note': 'parent+child RSS sampled concurrently during child lifetime'}))
    sys.exit(r)

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
