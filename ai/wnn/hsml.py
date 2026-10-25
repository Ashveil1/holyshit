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

class HSML:
    def __init__(self, seed=0):
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
        p, tried = induce(self.ctx['pairs'], **({} if self.induce_cap is None else {'cap': self.induce_cap}))
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
            self.ctx['pairs'].append((cx, y))
            self.pending = None
            return self._try_induce(s)
        pend['passed'] += 1
        if pend['passed'] >= 3:
            word = self.ctx['word']
            tot = self.ctx['tried_tot']
            SKILL_BY_WORD[word] = word
            self.mem.skills[word] = (pend['prog'], pend['fn'],
                {'source': 'dialog', 'tried': tot, 'examples': len(self.ctx['pairs']) + 3})
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
            h.mem.skills[t] = (prog, make_fn(prog), prov)
        for n, v in payload['attrs_C'].items():
            h.mem.attrs.C[n] = dict(v)
        SKILL_BY_WORD.update(payload['words'])
        return h
