"""hsml.py - ONE conversation entry point over ONE memory (B-534, LEDGER pre-reg 2026-10-25).
Every incoming sentence goes through HSML.hear(): naming/example/confirmation frames drive
dialog teaching (b529 induction protocol, zero-eval capture default post-B-533); statements
observe into attribute memory; queries go through the existing answer path; anything else
abstains. Frames + number parsing are DESIGNED (named). A skill taught mid-conversation is
stored in the SAME memory the query path reads and is immediately queryable."""
import os, pickle, random, re
from cur7 import make_fn, show_prog
import cur7 as C7
import b529
from b529 import induce, EX_RE, NAME_RE, CONF_RE
from b527 import HSMLMemory, derive_skills, load_logged, SKILL_BY_WORD, frame_num
from b521 import ATTRS

CONF_Q = 'ถ้า n เป็น {} ตอบอะไร'


# B-541: DESIGNED statement frames (from B-521's world generator) - fullmatch parsing
# grounds the name/attr token ROLES, enabling dynamic vocabulary learning.
STMT_FRAMES = [
    (re.compile(r'(\S+) มี (\S+) และ (\S+) และ (\S+)'), lambda m: (m.group(1), [m.group(2), m.group(3), m.group(4)])),
    (re.compile(r'(\S+) มี (\S+) และ (\S+)'), lambda m: (m.group(1), [m.group(2), m.group(3)])),
    (re.compile(r'(\S+) และ (\S+) ของ (\S+)'), lambda m: (m.group(3), [m.group(1), m.group(2)])),
    (re.compile(r'(\S+) นั้น มี (\S+)'), lambda m: (m.group(1), [m.group(2)])),
    (re.compile(r'(\S+) มี (\S+)'), lambda m: (m.group(1), [m.group(2)])),
    (re.compile(r'ดู (\S+) ของ (\S+)'), lambda m: (m.group(2), [m.group(1)])),
    (re.compile(r'(\S+) ของ (\S+) สวย'), lambda m: (m.group(2), [m.group(1)])),
]

# B-544: FINITE designed guard list (named: this is NOT general Thai understanding) -
# question/particle words must never be stored as names or attributes.
EN_GUARD = frozenset(['what', 'does', 'do', 'is', 'are', 'many', 'much', 'who',
                      'where', 'when', 'why', 'how', 'which', 'a', 'an', 'the',
                      'has', 'have'])  # B-547: finite designed English guard (named)
# B-549 (DESIGNED, finite, named): uncertainty markers - a statement containing one
# is NOT stored as fact (learn-while-chatting confidence separation).
UNCERTAIN_TH = frozenset(['อาจจะ', 'อาจ', 'น่าจะ', 'คงจะ', 'ไม่แน่ใจ', 'มั้ง'])
UNCERTAIN_EN = frozenset(['maybe'])
GUARD_WORDS = frozenset(['ไหม', 'มั้ย', 'หรือ', 'ใช่ไหม', 'อะไร',
                         'ครับ', 'ค่ะ', 'จ้า', 'นะ', 'ล่ะ', 'สิ'])
# question STEMS match by prefix: Thai glues them to nouns ('กี่ลักษณะ' is one token -
# run-1 of b544 caught exact-matching missing it). Designed heuristic, named limits:
# a legitimately taught word starting with a question stem would be refused too.
GUARD_STEMS = ('กี่', 'เท่าไหร่', 'เท่าไหร', 'ทำไม', 'เมื่อไหร่', 'ที่ไหน', 'ใคร', 'อย่างไร', 'อะไร')

def _guarded(w):
    return w in GUARD_WORDS or any(w.startswith(st) for st in GUARD_STEMS)

# B-542: DESIGNED negation frames - retraction of taught attribute facts.
NEG_FRAMES = [
    (re.compile(r'(\S+) ไม่มี (\S+) และ (\S+)'), lambda m: (m.group(1), [m.group(2), m.group(3)])),
    (re.compile(r'(\S+) ไม่มี (\S+)'), lambda m: (m.group(1), [m.group(2)])),
]

def _parse_negation(s):
    for rx, f in NEG_FRAMES:
        m = rx.fullmatch(s)
        if m:
            return f(m)
    return None

def _parse_statement(s):
    for rx, f in STMT_FRAMES:
        m = rx.fullmatch(s)
        if m:
            return f(m)
    return None

def _deps_of(prog, known, self_word):
    """B-539: scan a stored program for references to other stored skills (any nested
    symbol position). Returns the sorted dependency words, excluding the skill itself."""
    found = set()
    def walk(e):
        if isinstance(e, (tuple, list)):
            for x in e: walk(x)
        elif isinstance(e, str) and e in known and e != self_word:
            found.add(e)
    walk(prog)
    return sorted(found)

class HSML:
    def __init__(self, seed=0, induction_lib='separated'):  # B-536 verdict: separated is the default induction regime
        assert induction_lib in ('full', 'separated')
        self.induction_lib = induction_lib  # B-536: 'separated' excludes heavy pinned baselib from the SEARCH space only
        self.mem = HSMLMemory()
        self.mem.skills = derive_skills(load_logged())
        self.rng = random.Random(seed)
        self.ctx = None        # {'word':..., 'pairs':[...], 'rounds':int}
        self.pending = None    # {'prog':..., 'fn':..., 'checks':[cx,...], 'passed':int}
        self.log = []          # (sentence, response-kind, source)
        self.induce_cap = None  # None -> b529 default; B-534 Amendment 1 sets a bounded cap for C6

    def _rec(self, sentence, kind, source, **extra):
        self.log.append({'in': sentence, 'kind': kind, 'source': source, **extra})

    def hear(self, sentence):
        s = sentence.strip()
        m = NAME_RE.fullmatch(s)
        if m:
            word = m.group(1)
            # B-538 (DESIGNED, named): naming an existing word is a REVISION request.
            # Dialog-taught/loaded skills are revisable; seeded pinned-baselib skills are
            # reserved (provenance protection) - naming one abstains instead of clobbering.
            if word in self.mem.skills and self.mem.skills[word][2].get('source') == 'dialog':
                prov0 = self.mem.skills[word][2]
                if 'stale' in prov0:
                    # B-539: revalidation of a stale skill - confirm the STORED program
                    # executed under CURRENT dependencies (run() resolves names live).
                    prog0, fn0, _ = self.mem.skills[word]
                    checks = self.rng.sample(range(40, 400), 3)
                    self.ctx = {'word': word, 'pairs': [], 'rounds': 0, 'tried_tot': 0, 'revalidate': True}
                    self.pending = {'prog': prog0, 'fn': fn0, 'checks': checks, 'passed': 0, 'tried': 0, 'revalidate': True}
                    q = CONF_Q.format(checks[0])
                    self._rec(s, 'revalidate_opened', 'dialog', word=word)
                    return {'kind': 'revalidate_opened', 'text': q, 'source': 'dialog'}
                self.ctx = {'word': word, 'pairs': [], 'rounds': 0, 'tried_tot': 0, 'revision': True}
                self.pending = None
                self._rec(s, 'revision_opened', 'dialog', word=word)
                return {'kind': 'revision_opened', 'text': f'จะแก้วิธี {word} ใหม่', 'source': 'dialog'}
            if word in self.mem.skills or word in SKILL_BY_WORD:
                # reserved: seeded pinned-baselib word (mem.skills is keyed by TASK for
                # seeded skills; SKILL_BY_WORD resolves the Thai word -> task)
                self._rec(s, 'abstain', 'reserved', word=word)
                return {'kind': 'abstain', 'text': None, 'source': 'reserved', 'word': word}
            self.ctx = {'word': word, 'pairs': [], 'rounds': 0, 'tried_tot': 0}
            self.pending = None
            self._rec(s, 'naming', 'dialog', word=word)
            return {'kind': 'naming', 'text': f'รับทราบ วิธี {word}', 'source': 'dialog'}
        m = re.fullmatch(r'ถ้า n เป็น (\S+) ตอบ (\S+)', s)  # B-546: relaxed; _num validates
        if m:
            x, y = frame_num(m.group(1)), frame_num(m.group(2))
            if x is None or y is None:
                m = None  # malformed number word: fall through to today's routing
        if m:
            if self.ctx is None or self.pending is not None:
                self._rec(s, 'abstain', 'no-open-teaching-context')
                return {'kind': 'abstain', 'text': None, 'source': 'no-open-teaching-context'}
            self.ctx['pairs'].append((x, y))
            if len(self.ctx['pairs']) >= 5:
                return self._try_induce(s)
            self._rec(s, 'example', 'dialog', n=len(self.ctx['pairs']))
            return {'kind': 'example', 'text': f'จำไว้แล้ว {len(self.ctx["pairs"])} ตัวอย่าง', 'source': 'dialog'}
        m = re.fullmatch(r'ตอบ (\S+)', s)  # B-546: relaxed; _num validates
        if m:
            _cy = frame_num(m.group(1))
            if _cy is None:
                m = None
        if m:
            if self.pending is None:
                self._rec(s, 'abstain', 'no-pending-confirmation')
                return {'kind': 'abstain', 'text': None, 'source': 'no-pending-confirmation'}
            return self._confirm(s, _cy)
        # DESIGNED routing (named): skill query frame -> skill path; a sentence whose FIRST
        # token is an attribute word (or 'เขา') -> attr probe; otherwise a sentence containing
        # an attribute word -> declarative statement, observed into attr memory; else abstain.
        m2 = re.fullmatch(r'(\S+) ของ (\S+) คืออะไร', s)  # B-546: relaxed; _num validates
        if m2 and frame_num(m2.group(2)) is None:
            m2 = None  # not a number at all: fall through to today's routing
        toks = s.split()
        if m2:
            w0 = m2.group(1)
            t0 = SKILL_BY_WORD.get(w0, w0)
            if t0 in self.mem.skills and 'stale' in self.mem.skills[t0][2]:
                # B-539: a stale skill NEVER silently answers - explicit invalidation.
                self._rec(s, 'stale_skill', 'stale', word=w0)
                return {'kind': 'stale_skill', 'text': f'วิธี {w0} ต้องทบทวนก่อน', 'source': 'stale'}
            ans = self.mem.answer(s)
            if ans.get('kind') == 'skill_answer':
                src = ans.get('provenance', {}).get('source', '?')
                self._rec(s, 'skill_answer', src, skill=ans.get('skill'))
                return {'kind': 'skill_answer', 'text': ans['sentence'], 'source': src,
                        'result': ans['result']}
            self._rec(s, 'abstain', ans.get('kind', 'no_skill'))
            return {'kind': 'abstain', 'text': None, 'source': ans.get('kind', 'no_skill')}
        # B-540 run-1 fix (DESIGNED routing, named): an attr PROBE is a sentence whose
        # EVERY token is an attribute word (or 'เขา'); B-541: the vocabulary is DYNAMIC
        # (seed ATTRS + every attr ever stored).
        vocab = self.mem.attrs.vocab() if hasattr(self.mem.attrs, 'vocab') else set(ATTRS)
        # 'และ' allowed as probe conjunction (B-542 run-2 gap: 'X และ Y' probes were unrouted)
        if all(t in vocab or t in ('เขา', 'และ') for t in toks):
            ans = self.mem.answer(s)
            kind = ans.get('kind')
            self._rec(s, 'attr_' + str(kind), 'attr')
            if kind in ('unique', 'ambiguous'):
                return {'kind': 'attr_answer', 'text': str(ans.get('answer', ans.get('ext'))),
                        'source': 'attr', 'decision': kind}
            return {'kind': 'abstain', 'text': None, 'source': 'attr_' + str(kind)}
        # B-541 (DESIGNED, named): statements are parsed through the designed B-521
        # frames, which ground WHICH token is the name and which are attributes -
        # so both may be NEW words and are actually stored (no ack without learning:
        # the eval_ash baseline showed 'เหยี่ยว มี ปีก' was acknowledged but dropped).
        # A sentence with attr content but no designed frame abstains honestly.
        # B-543 (DESIGNED, named): reverse query 'X มี อะไรบ้าง' - checked BEFORE the
        # statement frames so 'อะไรบ้าง' can never be stored as an attribute.
        mrev = re.fullmatch(r'(\S+) มี อะไรบ้าง', s)
        if mrev is not None:
            name = mrev.group(1)
            attrs = self.mem.attrs.attrs_of(name) if hasattr(self.mem.attrs, 'attrs_of') else None
            self._rec(s, 'reverse_query', 'attr', name=name, found=attrs)
            if attrs:
                return {'kind': 'attr_list', 'text': f"{name} มี {' '.join(attrs)}",
                        'source': 'attr', 'name': name, 'attrs': attrs}
            # unknown name OR fully retracted: honest abstain, no fabricated list
            return {'kind': 'abstain', 'text': None,
                    'source': 'attr_reverse_' + ('empty' if attrs is not None else 'unknown')}
        # B-544 (DESIGNED): yes/no question 'X มี Y ไหม' - three-way honest answer:
        # taught -> ใช่; explicitly retracted -> ไม่; otherwise -> ไม่รู้ (absence != false).
        myn = re.fullmatch(r'(\S+) มี (\S+) ไหม', s)
        if myn is not None:
            name, attr = myn.group(1), myn.group(2)
            be = self.mem.attrs
            if _guarded(name) or _guarded(attr):
                self._rec(s, 'abstain', 'attr_guard'); return {'kind': 'abstain', 'text': None, 'source': 'attr_guard'}
            if hasattr(be, 'neg') and be.holds(name, attr):
                ans, truth = 'ใช่', 'yes'
            elif hasattr(be, 'neg') and be.neg(name, attr):
                ans, truth = 'ไม่', 'no_explicit'
            else:
                ans, truth = 'ไม่รู้', 'unknown'
            self._rec(s, 'yesno', 'attr', name=name, attr=attr, answer=truth)
            return {'kind': 'yesno', 'text': ans, 'source': 'attr', 'answer': truth}
        # B-548 (ALL DESIGNED, named): bounded two-hop composition over the taught
        # มี-graph. Question-conditioned content selection + sentence assembly from
        # taught words; every emitted link re-verified against LIVE memory at speak
        # time (no cache trusted at emission). Read-only: these frames never store.
        # NOT free sentence composition - finite designed frames, honestly named.
        mq3 = re.fullmatch(r'(\S+) มี อะไรที่มี (\S+) ที่มี (\S+)', s)
        if mq3 is not None:
            x, y, z = mq3.group(1), mq3.group(2), mq3.group(3)
            if _guarded(x) or _guarded(y) or _guarded(z):
                self._rec(s, 'abstain', 'attr_guard'); return {'kind': 'abstain', 'text': None, 'source': 'attr_guard'}
            return self._compose_three_hop(s, x, y, z, 'th', x, y, z)
        en3 = re.fullmatch(r'[Ww]hat does (\S+) have that has ([A-Za-z]\S+) that has ([A-Za-z]\S+)', s)
        if en3 is not None:
            rx = self._resolve_link(en3.group(1)); ry = self._resolve_link(en3.group(2).lower()); rz = self._resolve_link(en3.group(3).lower())
            for w0, r0 in ((en3.group(1), rx), (en3.group(2), ry), (en3.group(3), rz)):
                if r0[0] == 'amb':
                    self._rec(s, 'abstain', 'link_ambiguous', cands=r0[1])
                    return {'kind': 'abstain', 'text': f"'{w0}' can mean: {' '.join(r0[1])}", 'source': 'link_ambiguous'}
            x, y, z = rx[1], ry[1], rz[1]
            if _guarded(x) or _guarded(y) or _guarded(z):
                self._rec(s, 'abstain', 'attr_guard'); return {'kind': 'abstain', 'text': None, 'source': 'attr_guard'}
            return self._compose_three_hop(s, x, y, z, 'en', en3.group(1), en3.group(2), en3.group(3))
        mq = re.fullmatch(r'(\S+) มี อะไรที่มี (\S+)', s)
        if mq is not None:
            x, y = mq.group(1), mq.group(2)
            if _guarded(x) or _guarded(y):
                self._rec(s, 'abstain', 'attr_guard'); return {'kind': 'abstain', 'text': None, 'source': 'attr_guard'}
            return self._compose_two_hop(s, x, y, 'th', x, y)
        en_chain = re.fullmatch(r'[Ww]hat does (\S+) have that has ([A-Za-z]\S+)', s)
        if en_chain is not None:
            rx = self._resolve_link(en_chain.group(1)); ry = self._resolve_link(en_chain.group(2).lower())
            for w0, r0 in ((en_chain.group(1), rx), (en_chain.group(2), ry)):
                if r0[0] == 'amb':
                    self._rec(s, 'abstain', 'link_ambiguous', cands=r0[1])
                    return {'kind': 'abstain', 'text': f"'{w0}' can mean: {' '.join(r0[1])}", 'source': 'link_ambiguous'}
            x, y = rx[1], ry[1]
            if _guarded(x) or _guarded(y):
                self._rec(s, 'abstain', 'attr_guard'); return {'kind': 'abstain', 'text': None, 'source': 'attr_guard'}
            return self._compose_two_hop(s, x, y, 'en', en_chain.group(1), en_chain.group(2))
        # B-547 (ALL DESIGNED, finite - named: not learned understanding): bilingual slice.
        ml = re.fullmatch(r'(\S+) ภาษาอังกฤษคือ ([A-Za-z]\S*)', s)
        if ml is not None:
            th, en = ml.group(1), ml.group(2).lower()
            if _guarded(th) or en in EN_GUARD:
                self._rec(s, 'abstain', 'link_guard'); return {'kind': 'abstain', 'text': None, 'source': 'link_guard'}
            self.mem.links.setdefault(en, set()).add(th)
            self._rec(s, 'link_stored', 'dialog', en=en, th=th)
            return {'kind': 'link_stored', 'text': f'จำไว้แล้ว {en} = {th}', 'source': 'dialog'}
        mlr = re.fullmatch(r'(\S+) ภาษาอังกฤษไม่ใช่ ([A-Za-z]\S*)', s)
        if mlr is not None:
            th, en = mlr.group(1), mlr.group(2).lower()
            if en in self.mem.links and th in self.mem.links[en]:
                self.mem.links[en].discard(th)
                if not self.mem.links[en]: del self.mem.links[en]
                self._rec(s, 'link_retracted', 'dialog', en=en, th=th)
                return {'kind': 'link_retracted', 'text': 'ลบแล้ว', 'source': 'dialog'}
            self._rec(s, 'nothing_to_retract', 'dialog', en=en, th=th)
            return {'kind': 'nothing_to_retract', 'text': 'ไม่มีอะไรให้ลบ', 'source': 'dialog'}
        en_maybe = re.fullmatch(r'[Mm]aybe (.+)', s)
        if en_maybe is not None and re.fullmatch(r'(?:[Aa] |[Aa]n |[Tt]he )?\S+ has (?:[Aa] |[Aa]n |[Tt]he )?[A-Za-z]\S*(?: and (?:[Aa] |[Aa]n |[Tt]he )?[A-Za-z]\S*)?', en_maybe.group(1)):
            self._rec(s, 'uncertain_not_stored', 'dialog')
            return {'kind': 'uncertain_not_stored',
                    'text': 'ยังไม่แน่ใจ ขอยังไม่จำเป็นข้อเท็จจริง', 'source': 'dialog'}
        en_stmt = re.fullmatch(r'(?:[Aa] |[Aa]n |[Tt]he )?(\S+) has (?:[Aa] |[Aa]n |[Tt]he )?([A-Za-z]\S*)(?: and (?:[Aa] |[Aa]n |[Tt]he )?([A-Za-z]\S*))?', s)
        if en_stmt is not None:
            raw_name = en_stmt.group(1)
            raw_attrs = [g.lower() for g in en_stmt.groups()[1:] if g]
            toks_en = [raw_name] + raw_attrs
            if any(_guarded(t) or t.lower() in EN_GUARD for t in toks_en):
                self._rec(s, 'abstain', 'attr_guard'); return {'kind': 'unsupported_question', 'text': 'ยังไม่รองรับคำถามแบบนี้', 'source': 'attr_guard'}
            res = [self._resolve_link(t) for t in toks_en]
            amb = [r for r in res if r[0] == 'amb']
            if amb:
                self._rec(s, 'abstain', 'link_ambiguous', cands=amb[0][1])
                return {'kind': 'abstain', 'text': f"คำว่า '{toks_en[res.index(amb[0])]}' หมายถึงได้หลายคำ: {' '.join(amb[0][1])}", 'source': 'link_ambiguous'}
            name = res[0][1]; attrs = [r[1] for r in res[1:]]
            self.mem.attrs.observe_pairs(name, attrs)
            self._rec(s, 'observed', 'attr', name=name, attrs=attrs)
            return {'kind': 'observed', 'text': 'จำไว้แล้ว', 'source': 'attr'}
        en_rev = re.fullmatch(r'[Ww]hat does (?:[Aa] |[Aa]n |[Tt]he )?(\S+) have', s)
        if en_rev is not None:
            r0 = self._resolve_link(en_rev.group(1))
            if r0[0] == 'amb':
                self._rec(s, 'abstain', 'link_ambiguous', cands=r0[1])
                return {'kind': 'abstain', 'text': f"'{en_rev.group(1)}' can mean: {' '.join(r0[1])}", 'source': 'link_ambiguous'}
            attrs = self.mem.attrs.attrs_of(r0[1]) if hasattr(self.mem.attrs, 'attrs_of') else None
            self._rec(s, 'reverse_query_en', 'attr', name=r0[1], found=attrs)
            if attrs:
                return {'kind': 'attr_list', 'text': f"{en_rev.group(1)} has {' '.join(attrs)}", 'source': 'attr', 'name': r0[1], 'attrs': attrs}
            return {'kind': 'abstain', 'text': None, 'source': 'attr_reverse_en_' + ('empty' if attrs is not None else 'unknown')}
        en_yn = re.fullmatch(r'[Dd]oes (?:[Aa] |[Aa]n |[Tt]he )?(\S+) have (?:[Aa] |[Aa]n |[Tt]he )?([A-Za-z]\S+)', s)
        if en_yn is not None:
            rn = self._resolve_link(en_yn.group(1)); ra = self._resolve_link(en_yn.group(2).lower())
            for w0, r0 in ((en_yn.group(1), rn), (en_yn.group(2), ra)):
                if r0[0] == 'amb':
                    self._rec(s, 'abstain', 'link_ambiguous', cands=r0[1])
                    return {'kind': 'abstain', 'text': f"'{w0}' can mean: {' '.join(r0[1])}", 'source': 'link_ambiguous'}
            name, attr = rn[1], ra[1]
            if _guarded(name) or _guarded(attr):
                self._rec(s, 'abstain', 'attr_guard'); return {'kind': 'abstain', 'text': None, 'source': 'attr_guard'}
            be = self.mem.attrs
            if hasattr(be, 'neg') and be.holds(name, attr):
                ans, truth = 'yes', 'yes'
            elif hasattr(be, 'neg') and be.neg(name, attr):
                ans, truth = 'no', 'no_explicit'
            else:
                ans, truth = 'unknown', 'unknown'
            self._rec(s, 'yesno_en', 'attr', name=name, attr=attr, answer=truth)
            return {'kind': 'yesno', 'text': ans, 'source': 'attr', 'answer': truth}
        # B-549 (DESIGNED, named): confidence separation for in-chat learning.
        # Uncertain statements are NOT stored (honest reply, no negative evidence
        # either - uncertain != retracted). 'ไม่ใช่ <statement>' is a natural
        # correction: retract the inner statement's pairs via the B-542 path.
        toks_u = s.split()
        if any(t in UNCERTAIN_TH for t in toks_u):
            rest = ' '.join(t for t in toks_u if t not in UNCERTAIN_TH)
            if _parse_statement(rest) is not None:
                self._rec(s, 'uncertain_not_stored', 'dialog')
                return {'kind': 'uncertain_not_stored',
                        'text': 'ยังไม่แน่ใจ ขอยังไม่จำเป็นข้อเท็จจริง', 'source': 'dialog'}
        mcorr = re.fullmatch(r'ไม่ใช่ (.+)', s)
        if mcorr is not None:
            inner = _parse_statement(mcorr.group(1))
            if inner is None:
                self._rec(s, 'abstain', 'correction_unparsed')
                return {'kind': 'abstain', 'text': None, 'source': 'correction_unparsed'}
            name, attrs = inner
            gone = self.mem.attrs.unobserve(name, attrs)
            self._rec(s, 'correction', 'dialog', name=name, retracted=gone, asked=attrs)
            if gone:
                return {'kind': 'retracted', 'text': 'ลบแล้ว', 'source': 'dialog',
                        'name': name, 'retracted': gone,
                        'not_found': [a for a in attrs if a not in gone]}
            return {'kind': 'nothing_to_retract', 'text': 'ไม่มีอะไรให้ลบ', 'source': 'dialog',
                    'name': name, 'asked': attrs}
        stmt = _parse_statement(s)
        if stmt is not None:
            name, attrs = stmt
            # B-544: questions/particles are never stored as facts (nonmutation)
            if _guarded(name) or any(_guarded(a) for a in attrs):
                self._rec(s, 'abstain', 'attr_guard', name=name, attrs=attrs)
                return {'kind': 'unsupported_question', 'text': 'ยังไม่รองรับคำถามแบบนี้', 'source': 'attr_guard'}
            self.mem.attrs.observe_pairs(name, attrs)
            self._rec(s, 'observed', 'attr', name=name, attrs=attrs)
            return {'kind': 'observed', 'text': 'จำไว้แล้ว', 'source': 'attr'}
        # B-542: retraction through the designed negation frame. 'ลบแล้ว' is said ONLY
        # for attrs actually retracted (never-taught pairs report honestly, no fake ack).
        neg = _parse_negation(s)
        if neg is not None:
            name, attrs = neg
            gone = self.mem.attrs.unobserve(name, attrs)
            self._rec(s, 'retracted', 'attr', name=name, retracted=gone, asked=attrs)
            if gone:
                return {'kind': 'retracted', 'text': 'ลบแล้ว', 'source': 'attr',
                        'name': name, 'retracted': gone,
                        'not_found': [a for a in attrs if a not in gone]}
            return {'kind': 'nothing_to_retract', 'text': 'ไม่มีอะไรให้ลบ', 'source': 'attr',
                    'name': name, 'asked': attrs}
        self._rec(s, 'abstain', 'unrouted')
        return {'kind': 'abstain', 'text': None, 'source': 'unrouted'}

    def _compose_two_hop(self, s, x, y, lang, x_surf, y_surf):
        """B-548: candidates from memory; each emitted link re-verified LIVE at speak
        time (the verification gate). No verified path -> honest absence."""
        be = self.mem.attrs
        xs = be.attrs_of(x)
        verified = []
        if xs:
            for z in xs:
                # gate: re-query live memory at emission, both hops
                if be.holds(x, z) and be.holds(z, y):
                    verified.append(z)
        self._rec(s, 'compose', 'attr', x=x, y=y, verified=verified)
        if not verified:
            txt = 'ไม่รู้' if lang == 'th' else 'unknown'
            self._rec(s, 'compose_unknown', 'attr', x=x, y=y)
            return {'kind': 'compose_unknown', 'text': txt, 'source': 'attr'}
        if lang == 'th':
            text = ' / '.join(f'{x_surf} มี {z} และ {z} มี {y_surf}' for z in verified)
        else:
            text = ' / '.join(f'{x_surf} has {z} and {z} has {y_surf}' for z in verified)
        return {'kind': 'composed', 'text': text, 'source': 'attr', 'x': x, 'y': y, 'zs': verified}

    def _compose_three_hop(self, s, x, y, z, lang, x_surf, y_surf, z_surf):
        """B-551 (ALL DESIGNED, named): exactly-three-hop composition; same live
        re-verification gate as B-548. No verified path -> honest absence."""
        be = self.mem.attrs
        verified = []
        for a in (be.attrs_of(x) or []):
            # gate: re-query live memory at emission, all three hops
            if be.holds(x, a) and be.holds(a, y) and be.holds(y, z):
                verified.append(a)
        self._rec(s, 'compose3', 'attr', x=x, y=y, z=z, verified=verified)
        if not verified:
            txt = 'ไม่รู้' if lang == 'th' else 'unknown'
            self._rec(s, 'compose3_unknown', 'attr', x=x, y=y, z=z)
            return {'kind': 'compose_unknown', 'text': txt, 'source': 'attr'}
        if lang == 'th':
            text = ' / '.join(f'{x_surf} มี {a} และ {a} มี {y_surf} และ {y_surf} มี {z_surf}' for a in verified)
        else:
            text = ' / '.join(f'{x_surf} has {a} and {a} has {y_surf} and {y_surf} has {z_surf}' for a in verified)
        return {'kind': 'composed3', 'text': text, 'source': 'attr', 'x': x, 'y': y, 'z': z, 'as_': verified}

    def _resolve_link(self, w):
        """B-547: english surface word -> ('ok', canonical) or ('amb', [candidates]).
        Unlinked words keep their own surface form (dynamic vocabulary, B-541)."""
        c = self.mem.links.get(w) or self.mem.links.get(w.lower())
        if not c: return ('ok', w)
        if len(c) == 1: return ('ok', next(iter(c)))
        return ('amb', sorted(c))

    def _try_induce(self, s):
        self.ctx['rounds'] += 1
        if self.ctx['rounds'] > 3:
            word = self.ctx['word']; tried = self.ctx['tried_tot']; self.ctx = None
            self._rec(s, 'teach_failed', 'induction', word=word, tried=tried)
            return {'kind': 'teach_failed', 'text': None, 'source': 'induction', 'tried': tried}
        heavy = ('fact', 'sumto', 'square', 'choose2', 'dblfact')  # B-536: pinned recursive baselib
        popped = {}
        if self.induction_lib == 'separated':
            for k0 in heavy:
                if k0 in C7.LIB: popped[k0] = C7.LIB.pop(k0)
        if self.ctx.get('revision'):
            # B-538: the word being revised is excluded from its own revision's search
            # space - the corrected method must not be defined in terms of the method
            # being replaced (also keeps save/load rebuild safe: no self-reference).
            w0 = self.ctx['word']
            if w0 in C7.LIB: popped[w0] = C7.LIB.pop(w0)
        try:
            p, tried = induce(self.ctx['pairs'], **({} if self.induce_cap is None else {'cap': self.induce_cap}))
        finally:
            C7.LIB.update(popped)
        self.ctx['tried_tot'] += tried
        if p is None:
            word = self.ctx['word']; tried = self.ctx['tried_tot']; self.ctx = None
            self._rec(s, 'teach_failed', 'induction', word=word, tried=tried)
            return {'kind': 'teach_failed', 'text': None, 'source': 'induction', 'tried': tried}
        fn = make_fn(p)
        import cur7 as C; C.CAPF[0] = 20000
        checks = self.rng.sample(range(40, 400), 3)
        self.pending = {'prog': p, 'fn': fn, 'checks': checks, 'passed': 0, 'tried': tried}
        q = CONF_Q.format(checks[0])
        self._rec(s, 'confirmation_question', 'induction', tried=tried)
        return {'kind': 'confirmation_question', 'text': q, 'source': 'induction', 'tried': tried}

    def _confirm(self, s, y):
        pend = self.pending
        cx = pend['checks'][pend['passed']]
        pend['pairs_added'] = pend.get('pairs_added', 0) + 1
        try: ry = pend['fn'](cx, 1)
        except Exception: ry = None
        if ry != y:
            # failed confirmation: add the correcting pair, re-induce (b529 protocol)
            if pend.get('revalidate'):
                # B-539: teacher rejected the recomposed behavior -> convert to revision
                self.ctx['revision'] = True; self.ctx.pop('revalidate', None)
            self.ctx['pairs'].append((cx, y))
            self.pending = None
            return self._try_induce(s)
        pend['passed'] += 1
        if pend['passed'] >= 3 and pend.get('revalidate'):
            # B-539 revalidation accepted: stored program confirmed under current deps.
            word = self.ctx['word']
            prog0, fn0, prov0 = self.mem.skills[word]
            prov0.pop('stale')
            prov0['revalidated'] = prov0.get('revalidated', 0) + 1
            prov0['dep_rev'] = {d: self.mem.skills[d][2].get('revision', 0)
                                for d in prov0.get('deps', []) if d in self.mem.skills}
            C7.CAPF[0] = 20000
            C7.LIB[word] = (lambda ff: (lambda a, b: ff(a, b)))(fn0)
            C7.ev.cache_clear()  # B-539: no stale-cache residue after any confirmed change
            self._rec(s, 'skill_revalidated', 'dialog', word=word)
            self.ctx = None; self.pending = None
            return {'kind': 'skill_revalidated', 'text': f'ทบทวนวิธี {word} แล้ว', 'source': 'dialog'}
        if pend['passed'] >= 3:
            word = self.ctx['word']
            tot = self.ctx['tried_tot']
            SKILL_BY_WORD[word] = word
            # dialog-taught skills enter the induction LIB at store time (B-531 reuse path,
            # now in-conversation; same wrapping as b530.as_primitive / pin_lib)
            C7.CAPF[0] = 20000
            C7.LIB[word] = (lambda ff: (lambda a, b: ff(a, b)))(pend['fn'])
            prov = {'source': 'dialog', 'tried': tot, 'examples': len(self.ctx['pairs']) + 3}
            if self.ctx.get('revision') and word in self.mem.skills:
                # B-538: revision provenance - count + replaced program string recorded;
                # LIB registration above now wraps the NEW program (correction propagates).
                old_prog, _, old_prov = self.mem.skills[word]
                prov['revision'] = old_prov.get('revision', 0) + 1
                prov['replaces'] = show_prog(old_prog)
            # B-539: dependency provenance (which stored skills this program calls,
            # with each dependency's revision at store time)
            deps = _deps_of(pend['prog'], set(self.mem.skills) | set(SKILL_BY_WORD), word)
            if deps:
                prov['deps'] = deps
                prov['dep_rev'] = {d: self.mem.skills[d][2].get('revision', 0)
                                   for d in deps if d in self.mem.skills}
            self.mem.skills[word] = (pend['prog'], pend['fn'], prov)
            if 'revision' in prov:
                # B-539: explicit invalidation - every stored skill (TRANSITIVELY)
                # depending on the revised word is marked stale and leaves the induction
                # LIB until revalidated. Never a silent behavior change. Fixpoint over
                # deps so transitive dependents are marked too (a stale skill popped
                # from LIB would otherwise KeyError its own dependents at query time).
                r_new = prov['revision']
                changed = True
                while changed:
                    changed = False
                    for t, (p0, f0, pr0) in self.mem.skills.items():
                        if t == word or pr0.get('source') != 'dialog' or 'stale' in pr0:
                            continue
                        dep_list = pr0.get('deps', [])
                        direct = word in dep_list and pr0.get('dep_rev', {}).get(word, 0) != r_new
                        transitive = any(d in self.mem.skills and 'stale' in self.mem.skills[d][2]
                                         for d in dep_list)
                        if direct or transitive:
                            pr0['stale'] = {'dep': word, 'from_revision': pr0.get('dep_rev', {}).get(word, 0),
                                            'to_revision': r_new}
                            C7.LIB.pop(t, None)
                            changed = True
            C7.ev.cache_clear()  # B-539: no stale-cache residue after any successful store
            self._rec(s, 'skill_stored', 'induction', word=word, tried=tot,
                      prog=show_prog(pend['prog']))
            self.ctx = None; self.pending = None
            return {'kind': 'skill_stored', 'text': f'เก็บวิธี {word} แล้ว', 'source': 'induction', 'tried': tot}
        q = CONF_Q.format(pend['checks'][pend['passed']])
        self._rec(s, 'confirmation_question', 'induction', passed=pend['passed'])
        return {'kind': 'confirmation_question', 'text': q, 'source': 'induction'}

    def save(self, path, extra=None):
        """Persist the FULL learned state as data (B-535): skills {task: (prog, provenance)}
        (fn rebuilt on load), attr count table, dialog-added word map. Format-tagged."""
        payload = {'format': 'hsml-mem-1',
                   'skills': {t: (prog, prov) for t, (prog, fn, prov) in self.mem.skills.items()},
                   'attrs_C': {n: dict(v) for n, v in self.mem.attrs.C.items()},
                   'attrs_N': {n: sorted(v) for n, v in getattr(self.mem.attrs, 'N', {}).items()},
                   'words': dict(SKILL_BY_WORD),
                   'links': {k: sorted(v) for k, v in self.mem.links.items()}}
        if extra: payload.update(extra)
        with open(path, 'wb') as f: pickle.dump(payload, f)

    @classmethod
    def load(cls, path, seed=0):
        """Fresh HSML (baselib re-derived) + overlay saved learned state. Missing, corrupt or
        wrong-format files fail loudly - never a silent fresh memory (B-535 C6)."""
        if not os.path.exists(path):
            raise FileNotFoundError(f'hsml memory file missing: {path}')
        try:
            with open(path, 'rb') as f: payload = pickle.load(f)
        except Exception as e:
            raise RuntimeError(f'hsml memory file corrupt: {path} ({e})')
        if not isinstance(payload, dict) or payload.get('format') != 'hsml-mem-1':
            raise RuntimeError(f'hsml memory file wrong format: {path}')
        h = cls(seed=seed)
        C7.CAPF[0] = 20000
        for t, (prog, prov) in payload['skills'].items():
            fn = make_fn(prog)
            h.mem.skills[t] = (prog, fn, prov)
            # loaded skills rejoin the induction LIB (B-537: cross-session reuse path,
            # same registration as _confirm at store time); B-539: stale skills stay out
            # until revalidated (no building on unconfirmed foundations)
            if 'stale' not in prov:
                C7.LIB[t] = (lambda ff: (lambda a, b: ff(a, b)))(fn)
        for n, v in payload['attrs_C'].items():
            h.mem.attrs.C[n] = dict(v)
        # B-544: restore negative evidence (older saves without attrs_N default to empty)
        if hasattr(h.mem.attrs, 'N'):
            for n, v in payload.get('attrs_N', {}).items():
                h.mem.attrs.N[n] = set(v)
        for k, v in payload.get('links', {}).items():
            h.mem.links[k] = set(v)
        SKILL_BY_WORD.update(payload['words'])
        return h
