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
from b527 import HSMLMemory, derive_skills, load_logged, SKILL_BY_WORD
from b521 import ATTRS

CONF_Q = 'ถ้า n เป็น {} ตอบอะไร'

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
        m = EX_RE.fullmatch(s)
        if m:
            if self.ctx is None or self.pending is not None:
                self._rec(s, 'abstain', 'no-open-teaching-context')
                return {'kind': 'abstain', 'text': None, 'source': 'no-open-teaching-context'}
            x, y = int(m.group(1)), int(m.group(2))
            self.ctx['pairs'].append((x, y))
            if len(self.ctx['pairs']) >= 5:
                return self._try_induce(s)
            self._rec(s, 'example', 'dialog', n=len(self.ctx['pairs']))
            return {'kind': 'example', 'text': f'จำไว้แล้ว {len(self.ctx["pairs"])} ตัวอย่าง', 'source': 'dialog'}
        m = CONF_RE.fullmatch(s)
        if m:
            if self.pending is None:
                self._rec(s, 'abstain', 'no-pending-confirmation')
                return {'kind': 'abstain', 'text': None, 'source': 'no-pending-confirmation'}
            return self._confirm(s, int(m.group(1)))
        # DESIGNED routing (named): skill query frame -> skill path; a sentence whose FIRST
        # token is an attribute word (or 'เขา') -> attr probe; otherwise a sentence containing
        # an attribute word -> declarative statement, observed into attr memory; else abstain.
        m2 = re.fullmatch(r'(\S+) ของ (\d+) คืออะไร', s)
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
        if any(t in ATTRS or t == 'เขา' for t in toks):
            if toks[0] in ATTRS or toks[0] == 'เขา':
                ans = self.mem.answer(s)
                kind = ans.get('kind')
                self._rec(s, 'attr_' + str(kind), 'attr')
                if kind in ('unique', 'ambiguous'):
                    return {'kind': 'attr_answer', 'text': str(ans.get('answer', ans.get('ext'))),
                            'source': 'attr', 'decision': kind}
                return {'kind': 'abstain', 'text': None, 'source': 'attr_' + str(kind)}
            self.mem.attrs.observe(toks)
            self._rec(s, 'observed', 'attr')
            return {'kind': 'observed', 'text': 'จำไว้แล้ว', 'source': 'attr'}
        self._rec(s, 'abstain', 'unrouted')
        return {'kind': 'abstain', 'text': None, 'source': 'unrouted'}

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
                   'words': dict(SKILL_BY_WORD)}
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
        SKILL_BY_WORD.update(payload['words'])
        return h
