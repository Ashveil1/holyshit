"""hsml.py - ONE conversation entry point over ONE memory (B-534, LEDGER pre-reg 2026-10-25).
Every incoming sentence goes through HSML.hear(): naming/example/confirmation frames drive
dialog teaching (b529 induction protocol, zero-eval capture default post-B-533); statements
observe into attribute memory; queries go through the existing answer path; anything else
abstains. Frames + number parsing are DESIGNED (named). A skill taught mid-conversation is
stored in the SAME memory the query path reads and is immediately queryable."""
import os, pickle, random, re
import assoc
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
        self.assoc = assoc.Assoc()  # B-558: derived index, rebuilt from live store at proposal time
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
            attrs = self._attrs_of_any(name)
            own = list(attrs or [])
            inh = [(p, [t for t in ts if t not in own]) for p, ts in self._inherited_attrs(name)]
            inh = [(p, ts) for p, ts in inh if ts]
            self._rec(s, 'reverse_query', 'attr', name=name, found=attrs,
                      inherited={p: ts for p, ts in inh})
            if own or inh:
                text = f"{name} มี {' '.join(own)}" if own else ''
                for p, ts in inh:
                    text += (' และ' if text else f'{name} มี') + f'จาก {p}: {" ".join(ts)}'
                return {'kind': 'attr_list', 'text': text,
                        'source': 'attr', 'name': name, 'attrs': own,
                        'inherited': dict(inh)}
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
            pos, neged = self._pos_neg_any(name, attr)
            if pos and neged:
                ans, truth = 'ไม่รู้', 'conflict'  # B-553/B-554: surfaces or ancestors disagree
            elif pos:
                ans, truth = 'ใช่', 'yes'
            elif neged:
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
        # B-557 (ALL DESIGNED, named): the fixed 2-hop/3-hop compose frames are now ONE
        # bounded n-hop search: chain cap 3 attrs after the question head (= 4 verified
        # links), candidate-visit cap per question (recorded if hit), same live
        # re-verification gate + per-hop provenance as B-556. Longer chains -> honest
        # ไม่รู้/unknown (bounded by design). Behavior on existing 2/3-hop inputs unchanged.
        mchain = re.fullmatch(r'(\S+) มี อะไรที่มี (\S+(?: ที่มี \S+)*)', s)
        if mchain is not None:
            x = mchain.group(1); chain = mchain.group(2).split(' ที่มี ')
            if _guarded(x) or any(_guarded(c) for c in chain):
                self._rec(s, 'abstain', 'attr_guard'); return {'kind': 'abstain', 'text': None, 'source': 'attr_guard'}
            return self._compose_n_hop(s, x, chain, 'th', x, chain)
        enchain = re.fullmatch(r'[Ww]hat does (\S+) have that has ([A-Za-z]\S+(?: that has [A-Za-z]\S+)*)', s)
        if enchain is not None:
            x_surf = enchain.group(1); chain_surf = enchain.group(2).split(' that has ')
            rx = self._resolve_link(x_surf)
            rs = [self._resolve_link(w.lower()) for w in chain_surf]
            for w0, r0 in [(x_surf, rx)] + list(zip(chain_surf, rs)):
                if r0[0] == 'amb':
                    self._rec(s, 'abstain', 'link_ambiguous', cands=r0[1])
                    return {'kind': 'abstain', 'text': f"'{w0}' can mean: {' '.join(r0[1])}", 'source': 'link_ambiguous'}
            x = rx[1]; chain = [r0[1] for r0 in rs]
            if _guarded(x) or any(_guarded(c) for c in chain):
                self._rec(s, 'abstain', 'attr_guard'); return {'kind': 'abstain', 'text': None, 'source': 'attr_guard'}
            return self._compose_n_hop(s, x, chain, 'en', x_surf, chain_surf)
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
        # B-553 (ALL DESIGNED, named): Thai synonym intake while chatting.
        msyn = re.fullmatch(r'(\S+) กับ (\S+) คือคำเดียวกัน', s)
        if msyn is not None:
            x, y = msyn.group(1), msyn.group(2)
            if x == y or _guarded(x) or _guarded(y):
                self._rec(s, 'abstain', 'syn_guard'); return {'kind': 'abstain', 'text': None, 'source': 'syn_guard'}
            syn = self._syn()
            syn.setdefault(x, set()).add(y); syn.setdefault(y, set()).add(x)
            self._rec(s, 'syn_stored', 'dialog', x=x, y=y)
            return {'kind': 'syn_stored', 'text': 'จำไว้แล้ว', 'source': 'dialog'}
        msynr = re.fullmatch(r'(\S+) กับ (\S+) ไม่ใช่คำเดียวกัน', s)
        if msynr is not None:
            x, y = msynr.group(1), msynr.group(2)
            syn = self._syn()
            if y in syn.get(x, set()):
                syn[x].discard(y)
                if not syn[x]: del syn[x]
                if x in syn.get(y, set()):
                    syn[y].discard(x)
                    if not syn[y]: del syn[y]
                self._rec(s, 'syn_retracted', 'dialog', x=x, y=y)
                return {'kind': 'syn_retracted', 'text': 'ลบแล้ว', 'source': 'dialog'}
            self._rec(s, 'nothing_to_retract', 'dialog', x=x, y=y)
            return {'kind': 'nothing_to_retract', 'text': 'ไม่มีอะไรให้ลบ', 'source': 'dialog'}
        # B-554 (ALL DESIGNED, named): is-a relation, Thai single-token.
        misa = re.fullmatch(r'(\S+) เป็น (\S+)', s)
        if misa is not None:
            x, y = misa.group(1), misa.group(2)
            if x == y or _guarded(x) or _guarded(y):
                self._rec(s, 'abstain', 'isa_guard'); return {'kind': 'abstain', 'text': None, 'source': 'isa_guard'}
            self._isa().setdefault(x, set()).add(y)
            self._rec(s, 'isa_stored', 'dialog', x=x, y=y)
            return {'kind': 'isa_stored', 'text': 'จำไว้แล้ว', 'source': 'dialog'}
        misar = re.fullmatch(r'ไม่ใช่ (\S+) เป็น (\S+)', s)
        if misar is not None:
            x, y = misar.group(1), misar.group(2)
            isa = self._isa()
            if y in isa.get(x, set()):
                isa[x].discard(y)
                if not isa[x]: del isa[x]
                self._rec(s, 'isa_retracted', 'dialog', x=x, y=y)
                return {'kind': 'isa_retracted', 'text': 'ลบแล้ว', 'source': 'dialog'}
            self._rec(s, 'nothing_to_retract', 'dialog', x=x, y=y)
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
            attrs = self._attrs_of_any(r0[1])
            own = list(attrs or [])
            inh = [(p, [t for t in ts if t not in own]) for p, ts in self._inherited_attrs(r0[1])]
            inh = [(p, ts) for p, ts in inh if ts]
            self._rec(s, 'reverse_query_en', 'attr', name=r0[1], found=attrs,
                      inherited={p: ts for p, ts in inh})
            if own or inh:
                text = f"{en_rev.group(1)} has {' '.join(own)}" if own else ''
                for p, ts in inh:
                    text += (' and' if text else f"{en_rev.group(1)} has") + f" from {p}: {' '.join(ts)}"
                return {'kind': 'attr_list', 'text': text, 'source': 'attr', 'name': r0[1],
                        'attrs': own, 'inherited': dict(inh)}
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
            pos, neged = self._pos_neg_any(name, attr)
            if pos and neged:
                ans, truth = 'unknown', 'conflict'  # B-553/B-554: surfaces or ancestors disagree
            elif pos:
                ans, truth = 'yes', 'yes'
            elif neged:
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
            if (_parse_statement(rest) is not None
                    or re.fullmatch(r'\S+ กับ \S+ คือคำเดียวกัน', rest) is not None
                    or re.fullmatch(r'\S+ เป็น \S+', rest) is not None):
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
            gone = []
            for sw in self._synonyms(name):
                gone += [a for a in self.mem.attrs.unobserve(sw, attrs) if a not in gone]
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
                alt = self._assoc_fallback(s)  # B-558: abstention site is in scope for a verified proposal
                if alt is not None:
                    return alt
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
            gone = []
            for sw in self._synonyms(name):
                gone += [a for a in self.mem.attrs.unobserve(sw, attrs) if a not in gone]
            self._rec(s, 'retracted', 'attr', name=name, retracted=gone, asked=attrs)
            if gone:
                return {'kind': 'retracted', 'text': 'ลบแล้ว', 'source': 'attr',
                        'name': name, 'retracted': gone,
                        'not_found': [a for a in attrs if a not in gone]}
            return {'kind': 'nothing_to_retract', 'text': 'ไม่มีอะไรให้ลบ', 'source': 'attr',
                    'name': name, 'asked': attrs}
        # B-558 (EXPERIMENTAL, route A, pre-registered): bounded associative layer.
        # Fires ONLY when no designed frame matched. The index is rebuilt from the
        # LIVE store at proposal time (measured cheap at this scale, b558 C6) so it
        # can never be stale - retraction is exact by construction. Every proposed
        # fact is re-verified against live memory before being spoken (B-548
        # philosophy); the answer kind 'assoc_answer' keeps mechanism provenance
        # separable from exact-frame answers. Not language understanding: name-
        # anchored surface similarity over taught facts (assoc.py docstring).
        alt = self._assoc_fallback(s)  # B-558
        if alt is not None:
            return alt
        self._rec(s, 'abstain', 'unrouted')
        return {'kind': 'abstain', 'text': None, 'source': 'unrouted'}

    def _assoc_rebuild(self):
        """B-558: rebuild the associative index from the live store. Surfaces =
        canonical + synonyms (B-553) + linked EN words (B-547 reverse map). Only
        currently-held, non-retracted facts are indexed."""
        rev = {}
        for en, cans in (getattr(self.mem, 'links', None) or {}).items():
            for c in cans:
                rev.setdefault(c, []).append(en)
        name_surfaces = {}
        facts = {}
        for name in self.mem.attrs.C:
            held = []
            for a in (self._attrs_of_any(name) or []):
                pos, neged = self._pos_neg_any(name, a)
                if pos and not neged:
                    held.append(a)
            if not held:
                continue
            name_surfaces[name] = list({name} | self._synonyms(name)) + rev.get(name, [])
            for a in held:
                facts[(name, a)] = list({a} | self._synonyms(a)) + rev.get(a, [])
        self.assoc.rebuild(name_surfaces, facts)

    def _assoc_propose(self, s):
        """B-558: lazy rebuild (index = pure derived view, never stale) + propose."""
        self._assoc_rebuild()
        return self.assoc.propose(s)

    def _assoc_fallback(self, s):
        """B-558: propose + LIVE re-verification gate. Returns an assoc_answer
        response dict or None (caller falls through to its original abstention)."""
        pname, ranked, diag = self._assoc_propose(s)
        if pname is None or not ranked:
            return None
        verified = [f for f in ranked if self._has_via(*f)]
        if not verified:
            return None
        text = ' และ '.join(f'{n} มี {a}' for n, a in verified[:5])
        self._rec(s, 'assoc_answer', 'assoc', name=pname, facts=verified[:5], diag=diag)
        return {'kind': 'assoc_answer', 'text': text, 'source': 'assoc',
                'name': pname, 'facts': verified[:5], 'diag': diag}

    def _syn(self):
        syn = getattr(self.mem, 'syn', None)
        if syn is None:
            syn = {}
            self.mem.syn = syn
        return syn

    def _synonyms(self, w):
        """B-553: direct synonyms only (NOT transitive - named bound)."""
        out = {w}
        out |= self._syn().get(w, set())
        return out

    def _attrs_of_any(self, name):
        be = self.mem.attrs
        if not hasattr(be, 'attrs_of'):
            return None
        acc, known = [], False
        for w in self._synonyms(name):
            a = be.attrs_of(w)
            if a is not None:
                known = True
                for t in (a or []):
                    if t not in acc:
                        acc.append(t)
        return acc if acc else ([] if known else None)

    def _holds_any(self, x, y):
        be = self.mem.attrs
        return any(be.holds(sx, sy) for sx in self._synonyms(x) for sy in self._synonyms(y))

    def _neg_any(self, x, y):
        be = self.mem.attrs
        if not hasattr(be, 'neg'):
            return False
        return any(be.neg(sx, sy) for sx in self._synonyms(x) for sy in self._synonyms(y))

    def _isa(self):
        d = getattr(self.mem, 'isa', None)
        if d is None:
            d = {}
            self.mem.isa = d
        return d

    def _parents_any(self, name):
        """B-554: BFS over is-a parents of name and its synonyms. Depth cap 8,
        cycle-safe (visited set), depth-capped. Returns a LIST in deterministic BFS order (sorted within each level) - B-556 sweep run-1 found set-iteration order made provenance group order nondeterministic across processes (b555 C4 criterion was right, implementation wrong)."""
        seen = set(self._synonyms(name))
        frontier = sorted(seen)
        out = []
        for _ in range(8):
            nxt = set()
            for w in frontier:
                for p in self._isa().get(w, ()):  # child -> parents
                    if p not in seen:
                        seen.add(p)
                        out.append(p)
                        nxt.add(p)
            if not nxt:
                break
            frontier = sorted(nxt)
        return out

    def _pos_neg_any(self, name, attr):
        """B-554: aggregate positive/negative evidence for yes/no: own,
        synonyms, and is-a ancestors (all via live memory)."""
        pos = self._holds_any(name, attr)
        neg = self._neg_any(name, attr)
        for p in self._parents_any(name):
            if not pos and self._holds_any(p, attr):
                pos = True
            if not neg and self._neg_any(p, attr):
                neg = True
            if pos and neg:
                break
        return pos, neg

    def _inherited_attrs(self, name):
        """B-555: [(parent, [attrs])] in BFS order, deduped internally. Live memory."""
        groups = []
        seen = set()
        for p in self._parents_any(name):
            a = self._attrs_of_any(p)
            if a:
                fresh = [t for t in a if t not in seen]
                if fresh:
                    groups.append((p, fresh))
                    seen.update(fresh)
        return groups

    def _has_via(self, name, attr):
        """B-556: ('own', None) | ('inherited', parent) | None. Speakable iff the
        B-554 aggregation says pos and not neged; provenance prefers own, then the
        closest ancestor (BFS order) that holds the attr. Live memory."""
        pos, neged = self._pos_neg_any(name, attr)
        if not pos or neged:
            return None
        if self._holds_any(name, attr):
            return ('own', None)
        for p, _ts in self._inherited_attrs(name):
            if self._holds_any(p, attr):
                return ('inherited', p)
        return None

    def _attr_candidates(self, x):
        """B-556: own attrs first, then inherited (BFS), deduped. Live memory."""
        xs = list(self._attrs_of_any(x) or [])
        seen = set(xs)
        for _p, ts in self._inherited_attrs(x):
            for t in ts:
                if t not in seen:
                    seen.add(t)
                    xs.append(t)
        return xs

    COMPOSE_MAX_CHAIN = 3    # B-557: attrs after the question head -> at most 4 verified links
    COMPOSE_VISIT_CAP = 64   # B-557: candidates examined per question, recorded if hit

    def _compose_n_hop(self, s, x, chain, lang, x_surf, chain_surf):
        """B-557: one bounded n-hop path check replacing the fixed 2/3-hop pair.
        Candidates own-then-inherited (B-556 order); EVERY link on a candidate path
        re-verified LIVE at speak time via _has_via; per-hop provenance recorded.
        Chain longer than COMPOSE_MAX_CHAIN or no verified path -> honest absence.
        Fixed-depth verification only: cycles in the มี-graph cannot loop the search."""
        if len(chain) > self.COMPOSE_MAX_CHAIN:
            txt = 'ไม่รู้' if lang == 'th' else 'unknown'
            self._rec(s, 'compose_unknown', 'attr', x=x, chain=list(chain), reason='chain_too_long')
            return {'kind': 'compose_unknown', 'text': txt, 'source': 'attr'}
        verified = []; prov = []; visited = 0; capped = False
        for a in self._attr_candidates(x):
            if visited >= self.COMPOSE_VISIT_CAP:
                capped = True; break
            visited += 1
            hops = [self._has_via(x, a), self._has_via(a, chain[0])]
            ok = hops[0] is not None and hops[1] is not None
            for i in range(1, len(chain)):
                if not ok: break
                h = self._has_via(chain[i - 1], chain[i])
                hops.append(h)
                ok = h is not None
            if ok:
                verified.append(a); prov.append(tuple([a] + hops))
        kind = {1: 'composed', 2: 'composed3'}.get(len(chain), 'composed4')
        self._rec(s, 'compose', 'attr', x=x, chain=list(chain), verified=verified, prov=prov, visited=visited, capped=capped)
        if not verified:
            txt = 'ไม่รู้' if lang == 'th' else 'unknown'
            self._rec(s, 'compose_unknown', 'attr', x=x, chain=list(chain))
            return {'kind': 'compose_unknown', 'text': txt, 'source': 'attr'}
        have = 'มี' if lang == 'th' else 'has'
        joiner = ' และ ' if lang == 'th' else ' and '
        def _sentence(a):
            segs = [f'{x_surf} {have} {a}']
            prev = a
            for c in chain_surf:
                segs.append(f'{prev} {have} {c}')
                prev = c
            return joiner.join(segs)
        text = ' / '.join(_sentence(a) for a in verified)
        return {'kind': kind, 'text': text, 'source': 'attr', 'x': x, 'chain': list(chain),
                'zs': verified, 'as_': verified, 'prov': prov, 'capped': capped}

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
