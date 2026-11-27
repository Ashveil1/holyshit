#!/usr/bin/env python3
"""agent/core.holy conversation corpus vs an independent Python oracle.

Randomized sessions over the full command surface (remember / multi-fact
"is also" / recall and its aliases / user-taught paraphrases /
association recall / topic follow-ups / clarification dialogue /
session notes / list / say / help / garbage) run through
agent.core.respond; transcripts (replies + final memory dump) must match
the oracle byte for byte on every hosted execution route, and
agent/store.holy save/load roundtrips are checked on the reference route
(session state must NOT persist; pre-v3 file formats must migrate).
"""
import contextlib
import io
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import interp
import ir
import x64gen

env = dict(os.environ, HSROOT=str(ROOT), HSPATH=os.pathsep.join([
    str(ROOT), str(ROOT/'selfhost'), str(ROOT/'selfhost/be')]))

HELP = ("commands: remember <thing> is <fact> | remember <thing> is also "
        "<fact> | remember <thing> has <part> | remember <thing> เป็น <kind> | "
        "no, <thing> is <fact> | "
        "what is <thing> | do you know <thing> | what does <thing> mean | "
        "is <thing> in <thing> | is <thing> a <thing> | is <thing> <thing> | "
        "where is <thing> | "
        "what do you know about <thing> | "
        "how is <thing> | how about <thing> | <thing> คืออะไร | "
        "<thing> หมายความว่าอะไร | <thing> อยู่ไหน | "
        "<thing> เป็น <thing> ไหม | <thing> คือ <thing> หรือไม่ | "
        "and <thing> | what else | what about it | <phrase> means <thing> | "
        "forget <thing> | "
        "forget it | remember <thing> needs/can/uses/produces/causes <thing> | "
        "remember <thing> cannot <verb> | does <thing> <verb> <thing> | "
        "can <thing> <verb> | is <thing> needed by <thing> | "
        "remember <thing> is not a <kind> | what do you know | "
        "what did you forget | what did we talk about | note <text> | notes | "
        "clear notes | mode | mode strict | mode explore | hypotheses | "
        "hypotheses detail | forget hypothesis <thing> is a <kind> | "
        "clear hypotheses | read <text> | readings | readings about <thing> | "
        "readings detail | forget reading <thing> is a <kind> | "
        "clear readings | read url <url> (experimental, repl shell only) | "
        "read corpus <lineage>: <text> (offline corpus readings, UNVERIFIED) | list | say <text> | help")
WS = ' \t\n\r'
STOP = {'the', 'and', 'for', 'are', 'with', 'that', 'this'}
_READ_CAP = 100


def normalize(s):
    out = []
    ws = False
    for c in s:
        if c in WS:
            ws = True
        else:
            if ws and out:
                out.append(' ')
            out.append(c)
            ws = False
    return ''.join(out)


def lower_ascii(s):
    return ''.join(chr(ord(c) + 32) if 'A' <= c <= 'Z' else c for c in s)


def _ascii_byte(c):
    # Mirror core._ascii_byte (char model here: the corpus driver
    # runs the reference interpreter semantics).
    return c in '\t\n\r' or ' ' <= c <= '~'


def words(s):
    # Mirror core._words: split on single spaces, empty words dropped.
    return [w for w in s.split(' ') if w]


def nonascii(s):
    return any(ord(c) > 127 for c in s)


def sub_match(w, t):
    # Mirror core._sub: no length thresholds (interp counts characters,
    # the compiled backends count bytes); guards are model-independent.
    if not (nonascii(w) or nonascii(t)):
        return False
    if w != t:
        if w in t and (w != w[:1] or nonascii(w)):
            return True
        if t in w and (t != t[:1] or nonascii(t)):
            return True
    return False


def wmatch(w, t):
    return w == t or sub_match(w, t)


RELNEG = {'needs': 'does not need', 'can': 'cannot',
          'uses': 'does not use', 'produces': 'does not produce',
          'causes': 'does not cause', 'has': 'does not have',
          'is-a': 'is not'}
VERBT = [(' does not need ', 'needs', True), (' do not need ', 'needs', True),
         (' cannot ', 'can', True), (' can not ', 'can', True),
         (' does not use ', 'uses', True), (' do not use ', 'uses', True),
         (' does not produce ', 'produces', True), (' do not produce ', 'produces', True),
         (' does not cause ', 'causes', True), (' do not cause ', 'causes', True),
         (' needs ', 'needs', False), (' need ', 'needs', False),
         (' can ', 'can', False),
         (' uses ', 'uses', False), (' use ', 'uses', False),
         (' produces ', 'produces', False), (' produce ', 'produces', False),
         (' causes ', 'causes', False), (' cause ', 'causes', False)]
VERBQ = [(' need ', 'needs'), (' needs ', 'needs'),
         (' use ', 'uses'), (' uses ', 'uses'),
         (' produce ', 'produces'), (' produces ', 'produces'),
         (' cause ', 'causes'), (' causes ', 'causes'),
         (' have ', 'has'), (' has ', 'has')]
VERBP = [(' needed by ', 'needs'), (' used by ', 'uses'),
         (' produced by ', 'produces'), (' caused by ', 'causes')]
# A14: compositional inference rules [first premise, second premise,
# conclusion, display name] - a fixed inspectable table, the mirror of
# _RULES in agent/core.holy. can-stays-can: every rule with a 'can'
# premise concludes 'can'. 'has' is never a conclusion (non-transitive
# by design); 'needs'/'causes' appear in no rule.
RULES = [('has', 'uses', 'uses', 'has+uses', 'machine'),
         ('has', 'can', 'can', 'has+can', 'machine'),
         ('uses', 'can', 'can', 'uses+can', 'machine'),
         ('has', 'produces', 'produces', 'has+produces', 'machine'),
         ('uses', 'produces', 'produces', 'uses+produces', 'machine')]
RULECAP = 6


def negphrase(pred):
    return RELNEG.get(pred, 'not ' + pred)


def posphrase(pred):
    return 'is' if pred == 'is-a' else pred


def relvalue(v):
    return any(v.startswith(p) for p in
               ('needs ', 'can ', 'uses ', 'produces ', 'causes ',
                'does not ', 'cannot '))


def kind_value(v):
    p = lower_ascii(v)
    if p[:3] == 'in ' or p[:4] == 'has ':
        return False
    return not (v.startswith('คือ ') or v.startswith('หมายความว่า ') or
                v.startswith('อยู่ '))


BUILTIN_RELS = [
    ['mean', 'means', 'the definitional relation: X mean Y says the definition of X is Y'],
    ['is-in', 'means', 'the containment relation: X is in Y says X is inside Y'],
    ['is-a', 'means', 'the kind relation: X is a Y says X is a kind of Y'],
    ['has', 'means', 'the part relation: X has Y says Y is part of X'],
]


def stripart(s):
    if s[:3] == 'an ':
        return s[3:]
    if s[:2] == 'a ':
        return s[2:]
    return s


def unteach_is(reply, word):
    p = reply.find(' is ' + word + ' ')
    if p < 0:
        return reply
    return reply[:p] + ' ' + word + reply[p + 4 + len(word):]


def cwords(s):
    out = []
    for w in words(lower_ascii(s)):
        if w not in STOP and (len(w) >= 3 or nonascii(w)):
            if w not in out:
                out.append(w)
    return out


def _th_val(v):
    return v[len('คือ '):] if v.startswith('คือ ') else v


def thai_line(s):
    if not nonascii(s):
        return False
    return not any(('a' <= c <= 'z') or ('A' <= c <= 'Z') for c in s)


def join_th(values):
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return values[0] + ' และ ' + values[1]
    return ', '.join(values[:-1]) + ' และ ' + values[-1]


def join_values(values):
    n = len(values)
    if n == 1:
        return values[0]
    if n == 2:
        return values[0] + ' and ' + values[1]
    return ', '.join(values[:-1]) + ' and ' + values[-1]


class Oracle:
    """Fresh reference implementation of the agent.core spec."""

    def __init__(self):
        self.facts = {}      # key -> [value, ...]
        self.order = []
        self.aliases = {}    # phrase -> key
        self.notes = []
        self.topic = None
        self.pending = None  # {'cands': [...], 'keys': [...]}
        self.rels = []       # [subject, predicate, object]
        self.cooc = {}       # word -> {context word -> count}
        self.relset = {}     # subject -> predicate -> {object: True}
        self.relby = {}      # predicate -> stripped subject -> [[s, o], ...]
        self.forgotten = []  # A12 tombstones, capped at 20
        self.session = []    # A12 session log, capped at 10, never saved
        self.mode = 'strict'  # A14.1: session-only, like notes
        self.learned = None   # A21.2b: descriptors set by the repl
        self.learned_readings = []
        # A15: hypothesis candidates [subj, domain, count, created_ev,
        # later_uses, omitted] + retired [subj, domain, reason].
        self.hypotheses = []
        self.hyp_retired = []
        # A16: read candidates [subj, pred, obj, pos[], neg[],
        # pos_align, neg_align], session-only; read_src maps source
        # id -> raw payload body.
        self.readings = []
        self.read_src = {}
        self.read_n = 0
        self.url_srcs = []
        self.corpus_srcs = []
        self.test_fetch = False
        self.lang = 'en'
        self.register = 'khrup'

    def _particle(self):
        return 'ครับ'

    # --- A10 usage counting, mirroring core.holy ---
    def _cooc_add(self, key, value):
        ws = cwords(key)
        for w in cwords(value):
            if w not in ws:
                ws.append(w)
        for w in ws:
            for u in ws:
                if u != w:
                    ctx = self.cooc.setdefault(w, {})
                    ctx[u] = ctx.get(u, 0) + 1

    def _cooc_remove(self, key, value):
        ws = cwords(key)
        for w in cwords(value):
            if w not in ws:
                ws.append(w)
        for w in ws:
            ctx = self.cooc.get(w)
            if ctx is not None:
                for u in ws:
                    if u != w and ctx.get(u, 0) > 0:
                        ctx[u] -= 1

    def _usage_score(self, cand, awords):
        score = 0
        for w in cwords(cand):
            ctx = self.cooc.get(w)
            if ctx is not None:
                for a in awords:
                    if a != w and a in ctx:
                        score += ctx[a]
        return score

    def _usage_reply(self, asked):
        awords = cwords(asked)
        merged = {}
        for w in awords:
            ctx = self.cooc.get(w)
            if ctx is not None:
                for u, c in ctx.items():
                    if c > 0 and u not in awords:
                        merged[u] = merged.get(u, 0) + c
        if not merged:
            if self.lang == 'th':
                return 'ไม่รู้จัก' + self._particle() + ' ' + asked
            return 'i do not know ' + asked
        ranked = sorted(merged, key=lambda u: -merged[u])
        if self.lang == 'th':
            return ('ไม่เคยถูกสอน' + self._particle() + ' ' + asked +
                    ' แต่จากการใช้ ' + asked + ' น่าจะเกี่ยวกับ ' +
                    join_th(ranked[:3]))
        return ('i was never taught ' + asked +
                ', but from how you used it, ' + asked +
                ' seems related to ' + join_values(ranked[:3]))

    # --- A9 relations, mirroring core.holy ---
    def _rel_index(self, s, p, o):
        self.relset.setdefault(s, {}).setdefault(p, {})[o] = True
        self.relby.setdefault(p, {}).setdefault(stripart(s), []).append([s, o])

    def _add_rel(self, s, p, o):
        if o in self.relset.get(s, {}).get(p, {}):
            return
        self.rels.append([s, p, o])
        self._rel_index(s, p, o)
        # A16: user teaching is the ultimate verifier. Alignment is
        # tracked PER POLARITY (r[5] = positive side, r[6] = negative
        # side), separate from evidence status: the taught side is
        # marked CONFIRMED, recorded support on the other side is
        # marked DISPUTED, and any CONFLICT label stays. Teaching
        # never promotes anything into or out of the readings store.
        rp, rpol = p, 'pos'
        if len(p) > 4 and p[:4] == 'not-':
            rp, rpol = p[4:], 'neg'
        ri = self._read_find(s, rp, o)
        if ri >= 0:
            r = self.readings[ri]
            if rpol == 'pos':
                if r[3] and r[5] != 'confirmed':
                    r[5] = 'confirmed'
                    self._read_hist(r, 'confirmed', 'positive')
                if r[4] and r[6] != 'disputed':
                    r[6] = 'disputed'
                    self._read_hist(r, 'disputed', 'negative')
            else:
                if r[4] and r[6] != 'confirmed':
                    r[6] = 'confirmed'
                    self._read_hist(r, 'confirmed', 'negative')
                if r[3] and r[5] != 'disputed':
                    r[5] = 'disputed'
                    self._read_hist(r, 'disputed', 'positive')
        # A15: a taught domain verdict retires a matching hypothesis.
        if p in ('is-a', 'not-is-a'):
            d = o
            for art in ('a ', 'an ', 'the '):
                if d.startswith(art):
                    d = d[len(art):]
                    break
            self._hyp_retire(s, d,
                             'taught positive' if p == 'is-a' else 'taught negative')

    def _hyp_find(self, subj, domain):
        for i, h in enumerate(self.hypotheses):
            if h[0] == subj and h[1] == domain:
                return i
        return -1

    def _hyp_record(self, q, assum):
        order = []
        by = {}
        for a in assum:
            mk = a[0] + '|' + a[1]
            if mk in by:
                by[mk][2] += ', ' + a[3]
                by[mk][3] += ', ' + str(a[2])
            else:
                by[mk] = [a[0], a[1], a[3], str(a[2])]
                order.append(mk)
        ok = True
        for mk in order:
            c = by[mk]
            ev = [q, c[2], c[3]]
            i = self._hyp_find(c[0], c[1])
            if i >= 0:
                h = self.hypotheses[i]
                h[2] += 1
                if len(h[4]) < 10:
                    h[4].append(ev)
                else:
                    h[5] += 1
            elif len(self.hypotheses) >= 20:
                ok = False
            else:
                self.hypotheses.append([c[0], c[1], 1, ev, [], 0])
        return ok

    def _hyp_retire(self, s, domain, reason):
        i = self._hyp_find(s, domain)
        if i >= 0:
            h = self.hypotheses[i]
            self.hyp_retired.append([h[0], h[1], reason])
            self.hyp_retired = self.hyp_retired[-10:]
            self.hypotheses = self.hypotheses[:i] + self.hypotheses[i + 1:]

    def _hyp_q(self, x, pred, y):
        if pred == 'can':
            return 'can ' + x + ' ' + y
        return 'does ' + x + ' ' + pred[:-1] + ' ' + y

    def _hyp_reply(self, detail):
        hs = self.hypotheses
        if not hs:
            out = 'no open hypotheses'
        else:
            out = (('1 open hypothesis' if len(hs) == 1 else
                    str(len(hs)) + ' open hypotheses') +
                   ' (unresolved candidates, not beliefs):')
            labels = 'abcdefghijklmnopqrst'
            for i, h in enumerate(hs):
                out += ('\n(' + labels[i] + ') ' + h[0] + ' is a ' + h[1] +
                        ' - assumed ' + ('once' if h[2] == 1 else str(h[2]) + ' times') +
                        ", first for '" + h[3][0] + "'")
                if detail:
                    out += ("\n  created for '" + h[3][0] + "' [explore, rule " +
                            h[3][1] + ", step " + h[3][2] + "]")
                    for ev in h[4]:
                        out += ("\n  used for '" + ev[0] + "' [explore, rule " +
                                ev[1] + ", step " + ev[2] + "]")
                    if h[5] > 0:
                        out += '\n  (+' + str(h[5]) + ' older uses omitted)'
        if self.hyp_retired:
            out += '\nrecently retired:'
            for r in self.hyp_retired:
                out += '\n- ' + r[0] + ' is a ' + r[1] + ' (' + r[2] + ')'
        return out

    # --- A16 reader, mirroring core.holy ---
    def _read_find(self, s, p, o):
        for i, r in enumerate(self.readings):
            if r[0] == s and r[1] == p and r[2] == o:
                return i
        return -1

    def _read_directive(self, sent):
        # A19: fixed command-form set, whole-segment exact/prefix
        # matches only. No general imperative parser.
        ls = lower_ascii(sent)
        for p in ('remember ', 'no, ', 'mode ', 'clear ', 'forget ',
                  'read ', 'note ', 'say '):
            if len(ls) > len(p) and ls[:len(p)] == p:
                return True
        return ls in ('quit', 'exit', 'help', 'list', 'notes',
                      'readings', 'readings detail', 'hypotheses',
                      'hypotheses detail', 'click here',
                      'subscribe now', 'download this file')

    @staticmethod
    def _script_transitions(sent):
        # A19: ASCII/non-ASCII class changes at element boundaries,
        # ignoring spaces. UTF-8 Thai continuation bytes are all
        # non-ASCII, so byte and char models agree.
        out, prev = [], 0
        for i, ch in enumerate(sent):
            cl = 0
            if ch != ' ':
                cl = 1 if _ascii_byte(ch) else 2
            if cl:
                if prev and cl != prev:
                    out.append(i)
                prev = cl
        return out

    def _read_skip(self, sent):
        # A17: primary skip-reason, precedence quoted/attributed >
        # directive (A19) > modal/hedged > multi-clause, one count
        # per segment.
        if '"' in sent or "'" in sent:
            return 'quoted'
        ls = ' ' + lower_ascii(sent) + ' '
        if (' says ' in ls or ' said ' in ls or
                ' according to ' in ls):
            return 'quoted'
        if self._read_directive(sent):
            return 'directive'
        for w in (' might ', ' may ', ' could ', ' should ', ' would ',
                  ' must ', ' probably ', ' maybe ', ' perhaps '):
            if w in ls:
                return 'modal-hedged'
        if ',' in sent or ';' in sent:
            return 'multi-clause'
        return ''

    def _read_pron(self, subj):
        return subj in ('i', 'you', 'he', 'she', 'it', 'we', 'they',
                        'there')

    def _read_extract(self, sent):
        ex = self._read_extract0(sent)
        if ex is not None and self._read_pron(ex[0]):
            return None
        return ex

    def _read_extract0(self, sent):
        ls = lower_ascii(sent)
        for marker, pred, pol, pid in (
                (' ไม่เป็น ', 'is-a', 'neg', 'thai-not-is-a'),
                (' เป็น ', 'is-a', 'pos', 'thai-is-a'),
                (' อยู่ ', 'is-in', 'pos', 'thai-is-in'),
                (' คือ ', 'means', 'pos', 'thai-means')):
            k = sent.find(marker)
            if k > 0 and k + len(marker) < len(sent):
                return [sent[:k], pred, sent[k + len(marker):], pol, pid]
        # objects keep their leading article, matching taught relations
        # A17: plural forms registered with distinct pattern ids,
        # negatives before positives. The trailing constant is the
        # exact minimum-length guard, mirroring core.holy.
        for marker, pred, pol, pid, off, guard in (
                (' is not a ', 'is-a', 'neg', 'not-is-a', 8, 11),
                (' is not an ', 'is-a', 'neg', 'not-is-a', 8, 12),
                (' is in ', 'is-in', 'pos', 'is-in', 7, 7),
                (' is a ', 'is-a', 'pos', 'is-a', 4, 6),
                (' is an ', 'is-a', 'pos', 'is-a', 4, 7),
                (' is ', 'is-a', 'pos', 'is-a-bare', 4, 4),
                (' has ', 'has', 'pos', 'has', 5, 6),
                (' do not have ', 'has', 'neg', 'not-have', 13, 13),
                (' does not have ', 'has', 'neg', 'not-have', 15, 15),
                (' are not ', 'is-a', 'neg', 'not-are', 9, 9),
                (' are ', 'is-a', 'pos', 'are', 5, 5),
                (' have ', 'has', 'pos', 'have', 6, 6)):
            k = ls.find(marker)
            if k > 0 and k + guard < len(ls):
                return [ls[:k], pred, ls[k + off:], pol, pid]
        for marker, pred, neg in VERBT:
            k = ls.find(marker)
            if k > 0 and k + len(marker) < len(ls):
                return [ls[:k], pred, ls[k + len(marker):],
                        'neg' if neg else 'pos', pred]
        return None

    def _read_obj_ok(self, ex):
        return ' is ' not in ex[2] and ' and ' not in ex[2]

    # A18 URL policy mirror (EXPERIMENTAL preview).
    def _url_test_mode(self):
        # Mirrors the repl-set state flag; never the process env.
        return self.test_fetch

    def _url_bad_host(self, host):
        if not host or '..' in host:
            return True
        return any(not ('a' <= c <= 'z' or '0' <= c <= '9' or
                        c in '.-') for c in host)

    def _url_priv4(self, host):
        parts = host.split('.')
        if len(parts) != 4:
            return False
        nums = []
        for p in parts:
            if not p or len(p) > 3 or not p.isdigit():
                return False
            nums.append(int(p))
        a, b = nums[0], nums[1]
        return (a in (0, 10, 127) or a >= 224 or
                (a == 169 and b == 254) or (a == 192 and b == 168) or
                (a == 172 and 16 <= b <= 31))

    def _url_norm(self, url, test_mode=None):
        if '\r' in url or '\n' in url:
            return [False, 'bad url (control characters)']
        if len(url) < 8 or lower_ascii(url[:7]) != 'http://':
            return [False, 'only http:// urls are supported']
        rest = url[7:]
        h = rest.find('#')
        if h >= 0:
            rest = rest[:h]
        p = rest.find('/')
        authority, path = (rest[:p], rest[p:]) if p >= 0 else (rest, '/')
        if '@' in authority:
            return [False, 'embedded credentials are not allowed']
        host, port, hasport = authority, 80, False
        c = authority.find(':')
        if c >= 0:
            host, ps = authority[:c], authority[c + 1:]
            if not ps or len(ps) > 5 or not ps.isdigit():
                return [False, 'bad port']
            port = int(ps)
            if port < 1 or port > 65535:
                return [False, 'bad port']
            hasport = True
        host = lower_ascii(host)
        if self._url_bad_host(host):
            return [False, 'bad host']
        if not (self._url_test_mode() if test_mode is None else test_mode):
            if port != 80:
                return [False, 'only port 80 is supported']
            if self._url_priv4(host):
                return [False,
                        'private or reserved addresses are not allowed']
        norm = 'http://' + host
        if hasport and port != 80:
            norm += ':' + str(port)
        return [True, norm + path]

    def _url_src(self, norm):
        for i, e in enumerate(self.url_srcs):
            if e[0] == norm:
                return 'url-' + str(i + 1)
        if len(self.url_srcs) >= 100:
            return ''
        self.url_srcs.append([norm, 0])
        return 'url-' + str(len(self.url_srcs))

    def _corpus_src(self, lin):
        # A19: one corpus lineage = one corpus-N source, forever.
        for i, e in enumerate(self.corpus_srcs):
            if e == lin:
                return 'corpus-' + str(i + 1)
        if len(self.corpus_srcs) >= 100:
            return ''
        self.corpus_srcs.append(lin)
        return 'corpus-' + str(len(self.corpus_srcs))

    def _read_corpus(self, rest):
        # Mirrors core._read_corpus: lineage id + ': ' + payload.
        k = rest.find(': ')
        if k <= 0 or k > 40:
            return ("read corpus: expected 'read corpus <lineage-id>: "
                    "<text>'")
        lin = rest[:k]
        ok = all(('a' <= c <= 'z') or ('0' <= c <= '9') or
                 c in '-_' for c in lin)
        if not ok:
            return 'read corpus: lineage id uses a-z, 0-9, - and _ only'
        src = self._corpus_src(lin)
        if src == '':
            return ('read corpus: source registry full (100 distinct '
                    'sources); clear readings to start over')
        return self._read_ingest(src, rest[k + 2:], False)

    def _read_url(self, raw):
        # Mirrors the core route: validation here, fetch in the shell.
        r = self._url_norm(raw, self._url_test_mode())
        if not r[0]:
            return 'read url: ' + r[1]
        return ('read url: url reading is only available in the repl '
                'shell (experimental)')

    def _read_ids(self, side):
        out = ''
        for se in side:
            out = se[0] if not out else out + ', ' + se[0]
        return out

    def _read_text(self, rest):
        src = ''
        body = rest
        k = rest.find(': ')
        if 0 < k <= 20:
            nm = rest[:k]
            ok = all(('a' <= c <= 'z') or ('0' <= c <= '9') or
                     c in '-_' for c in nm)
            if ok:
                src, body = nm, rest[k + 2:]
        if not src:
            self.read_n += 1
            src = 'read-' + str(self.read_n)
        return self._read_ingest(src, body, False)

    def _read_ingest(self, src, body, truncated):
        self.read_src[src] = body
        segs, cur = [], ''
        i = 0
        while i < len(body):
            ch = body[i]
            if ch in '.!?' and (i + 1 >= len(body) or body[i + 1] == ' '):
                if cur:
                    segs.append(cur)
                cur = ''
                if i + 1 < len(body):
                    i += 1
            else:
                cur += ch
            i += 1
        if cur:
            segs.append(cur)
        matched = newc = upd = ref = dup = 0
        sk_q = sk_m = sk_c = sk_d = sk_tb = um = 0
        lr = lamb = 0
        warns, wkeys = [], []
        for sent in segs:
            sk = self._read_skip(sent)
            if sk == 'quoted':
                sk_q += 1
            elif sk == 'directive':
                sk_d += 1
            elif sk == 'modal-hedged':
                sk_m += 1
            else:
                exs = []
                if not sk:
                    trs = self._script_transitions(sent)
                    tb_skip = False
                    if trs:
                        # A19 Thai-Latin boundary: split only when
                        # BOTH sides independently match complete
                        # supported patterns; first valid split
                        # wins; otherwise the whole segment is
                        # skipped as thai-boundary-ambiguous.
                        tb_ok = False
                        for ti in trs:
                            if not tb_ok:
                                le = sent[:ti].rstrip(' ')
                                ri = sent[ti:].lstrip(' ')
                                if le and ri:
                                    exl = self._read_extract(le)
                                    exr = self._read_extract(ri)
                                    if (exl is not None and
                                            exr is not None and
                                            self._read_obj_ok(exl) and
                                            self._read_obj_ok(exr)):
                                        exs.append([exl, le])
                                        exs.append([exr, ri])
                                        tb_ok = True
                        if not tb_ok:
                            tb_skip = True
                    ka = -1 if trs else lower_ascii(sent).find(' and ')
                    if tb_skip:
                        sk = 'thai-boundary-ambiguous'
                    elif ka > 0:
                        # A17: split at the FIRST exact ' and ', both
                        # sides must match, strictly atomic, no
                        # recursion, spans are the side texts.
                        exl = self._read_extract(sent[:ka])
                        exr = self._read_extract(sent[ka + 5:])
                        if (exl is not None and exr is not None and
                                self._read_obj_ok(exl) and
                                self._read_obj_ok(exr)):
                            exs.append([exl, sent[:ka]])
                            exs.append([exr, sent[ka + 5:]])
                        else:
                            sk = 'multi-clause'
                    else:
                        if not trs:
                            ex = self._read_extract(sent)
                            if ex is not None and self._read_obj_ok(ex):
                                exs.append([ex, sent])
                            else:
                                um += 1
                                if self.learned:
                                    a_, b_ = self._learned_scan(src, sent)
                                    lr += a_
                                    lamb += b_
                if sk == 'multi-clause':
                    sk_c += 1
                if sk == 'thai-boundary-ambiguous':
                    sk_tb += 1
                for ex, span in exs:
                    matched += 1
                    rj = -1
                    ri2 = self._read_find(ex[0], ex[1], ex[2])
                    if ri2 >= 0:
                        r = self.readings[ri2]
                        side = r[3] if ex[3] == 'pos' else r[4]
                        if any(se[0] == src for se in side):
                            dup += 1
                        else:
                            side.append([src, span, ex[4]])
                            upd += 1
                            rj = ri2
                    elif len(self.readings) >= _READ_CAP:
                        ref += 1
                    else:
                        entry = [src, span, ex[4]]
                        if ex[3] == 'neg':
                            self.readings.append(
                                [ex[0], ex[1], ex[2], [], [entry], '', '', []])
                        else:
                            self.readings.append(
                                [ex[0], ex[1], ex[2], [entry], [], '', '', []])
                        newc += 1
                        rj = len(self.readings) - 1
                    # A19: a later conflicting reading raises an
                    # evidence-review warning (CONFLICT across
                    # sources, SCOPE_MISMATCH inside one source);
                    # accepted knowledge is never altered.
                    if rj >= 0:
                        r = self.readings[rj]
                        if r[3] and r[4]:
                            wk = r[0] + ' | ' + r[1] + ' | ' + r[2]
                            if wk not in wkeys:
                                wkeys.append(wk)
                                internal = any(
                                    se[0] == se2[0]
                                    for se in r[3] for se2 in r[4])
                                wt = ('SCOPE_MISMATCH' if internal
                                      else 'CONFLICT')
                                warns.append(wt + ' on ' + wk)
        out = (src + ': ' + str(len(segs)) + ' segments in, ' +
               str(matched) + ' pattern matches, ' + str(matched) +
               ' candidates extracted (' + str(newc) + ' new, ' +
               str(upd) + ' updated, ' + str(ref) + ' refused, ' +
               str(dup) + ' repeat), ' +
               str(sk_q + sk_m + sk_c + sk_d + sk_tb) +
               ' skipped (' + str(sk_q) + ' quoted, ' + str(sk_d) +
               ' directive, ' + str(sk_m) +
               ' modal-hedged, ' + str(sk_c) + ' multi-clause, ' +
               str(sk_tb) + ' thai-boundary-ambiguous), ' +
               str(um) + ' unmatched')
        if lr > 0 or lamb > 0:
            out += ('; ' + str(lr) + ' learned-pattern readings recorded'
                    ' (LEARNED_PATTERN, UNVERIFIED, not facts; ' +
                    str(lamb) + ' ambiguous segments)')
        for w in warns:
            out += ('; evidence-review ' + w +
                    ' - accepted knowledge unchanged')
        if truncated:
            out += ' (text truncated at 64KB)'
        return out

    # A21.2b: learned-pattern matcher (independent of agent.patgen).
    _LSTOP = ('not no never nor and or but might may could would should '
              'must can cannot will shall says said say claims claim '
              'according that because if unless although while when '
              'where which who whom whose then however also maybe '
              'perhaps probably possibly allegedly reportedly it he she '
              'they this these those we i you remember read '
              'forget').split()

    def _learned_match(self, vt, text):
        if any(ord(c) > 127 for c in text):
            return None
        t = ' '.join(lower_ascii(text).split()).split(' ') \
            if text.strip() else []
        t = [x for x in t] if t != [''] else []
        n, m = len(t), len(vt)
        if m < 1:
            return None
        idx = [i for i in range(n - m + 1) if t[i:i + m] == vt]
        if len(idx) != 1:
            return None
        f = idx[0]

        def alnum(x):
            return x != '' and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789'
                                   for c in x)

        def slot(a, b):
            return (1 <= b - a <= 4 and
                    all(alnum(x) and x not in self._LSTOP for x in t[a:b]))
        if not slot(0, f) or not slot(f + m, n):
            return None
        if not all(alnum(x) for x in vt):
            return None
        return [' '.join(t[:f]), ' '.join(t[f + m:])]

    def _learned_scan(self, src, sent):
        hits = []
        for d in self.learned:
            r = self._learned_match(d[1].split(' '), sent)
            if r is not None:
                hits.append([r[0], d[2], r[1], d[3], d[0]])
        if not hits:
            return 0, 0
        added = 0
        for h in hits:
            dup = any(e[:5] == h and e[5] == src
                      for e in self.learned_readings)
            if not dup and len(self.learned_readings) < 200:
                self.learned_readings.append(
                    h + [src, sent, len(hits) > 1])
                added += 1
        return added, (1 if len(hits) > 1 else 0)

    # A19 publisher-lineage map (versioned, additive-only):
    # [corpus lineage id, registrable domain, publisher group].
    def _lineage_map(self):
        return [['simplewiki-corpus', 'wikipedia.org', 'wikipedia']]

    def _lineage_map_version(self):
        return '1'

    def _pub_for_domain(self, d):
        for e in self._lineage_map():
            if e[1] == d:
                return e[2]
        return ''

    def _pub_for_lineage(self, lin):
        for e in self._lineage_map():
            if e[0] == lin:
                return e[2]
        return ''

    def _corpus_lineage(self, src):
        # The lineage id behind a corpus-N source id, or ''.
        if len(src) > 7 and src[:7] == 'corpus-':
            ns = src[7:]
            if ns and ns.isdigit():
                n = int(ns)
                if 1 <= n <= len(self.corpus_srcs):
                    return self.corpus_srcs[n - 1]
        return ''

    def _src_domain(self, src):
        # A19: url-N -> registry host; dotted-quad literal is its
        # own domain; else last two host labels (approximation).
        # Typed sources have no domain.
        if len(src) > 4 and src[:4] == 'url-':
            ns = src[4:]
            if not ns or not ns.isdigit():
                return ''
            n = int(ns)
            if 1 <= n <= len(self.url_srcs):
                rest = self.url_srcs[n - 1][0][7:]
                host = rest.split('/')[0].split(':')[0]
                parts = host.split('.')
                if len(parts) == 4 and all(
                        p and p.isdigit() for p in parts):
                    return host
                if len(parts) >= 2:
                    return parts[-2] + '.' + parts[-1]
                return host
        return ''

    def _read_ev_parts(self, side):
        # A20 (GPT binding): content clusters are NOT_ASSESSED -
        # sentence similarity does not prove copying - so the A19
        # shingle clustering is retired and no longer measured.
        # Corpus sources group by lineage (through the publisher map);
        # a url whose domain maps to the same publisher as a corpus
        # lineage on the side is ABSORBED into that group. HTTP-only
        # sides behave exactly as before.
        cgroups = []
        for se in side:
            lin = self._corpus_lineage(se[0])
            if lin != '':
                g = self._pub_for_lineage(lin) or 'corpus:' + lin
                if g not in cgroups:
                    cgroups.append(g)
        doms, nodom, nurl = [], 0, 0
        for se in side:
            if self._corpus_lineage(se[0]) != '':
                continue
            d = self._src_domain(se[0])
            if d == '':
                nodom += 1
            else:
                p = self._pub_for_domain(d)
                if not (p != '' and p in cgroups):
                    nurl += 1
                    if d not in doms:
                        doms.append(d)
        return [len(doms), nodom, len(cgroups), nurl]

    def _read_ev(self, side):
        # A19: agreeing sources and registrable-domain diversity as
        # separate fields; A20: content clusters NOT_ASSESSED.
        p = self._read_ev_parts(side)
        out = (str(len(side)) + ' agreeing source' +
               ('s' if len(side) > 1 else ''))
        out += (', ' + str(p[0]) + ' registrable domain' +
                ('' if p[0] == 1 else 's'))
        if p[1]:
            out += ' (' + str(p[1]) + ' without)'
        if p[2]:
            out += (', ' + str(p[2]) + ' corpus lineage' +
                    ('' if p[2] == 1 else 's') +
                    ' (lineage map v' + self._lineage_map_version() + ')')
        out += ', content clusters NOT_ASSESSED'
        return out

    def _read_eligible(self, side, other, align):
        # A20: SOURCE_DIVERSITY_THRESHOLD_MET (renamed from A19
        # REVIEW_ELIGIBLE) is an evidence status, never a fact.
        if len(side) >= 3 and not other and align == '':
            p = self._read_ev_parts(side)
            return p[0] >= 2
        return False

    def _readings_reply(self, about, detail):
        rs = self.readings
        if about != '':
            rs = [r for r in rs if r[0] == about]
        if not rs:
            return 'no readings' if about == '' else \
                'no readings about ' + about
        out = str(len(rs)) + ' read candidate'
        if len(rs) > 1:
            out += 's'
        if about != '':
            out += ' about ' + about
        out += ' (unverified readings, not facts):'
        labels = 'abcdefghijklmnopqrstuvwxyz'
        for i, r in enumerate(rs):
            out += ('\n(' + labels[i] + ') ' if i < 26
                    else '\n(' + str(i + 1) + ') ')
            out += r[0] + ' | ' + r[1] + ' | ' + r[2] + ' - '
            parts = ''
            if r[3]:
                parts = ('positive support: ' + str(len(r[3])) +
                         ' source' + ('s' if len(r[3]) > 1 else '') +
                         ' (' + self._read_ids(r[3]) + ')')
                if r[5] == 'confirmed':
                    parts += ' [USER_CONFIRMED]'
                if r[5] == 'disputed':
                    parts += ' [USER_DISPUTED]'
            if r[4]:
                if parts:
                    parts += '; '
                parts += ('negative support: ' + str(len(r[4])) +
                          ' source' + ('s' if len(r[4]) > 1 else '') +
                          ' (' + self._read_ids(r[4]) + ')')
                if r[6] == 'confirmed':
                    parts += ' [USER_CONFIRMED]'
                if r[6] == 'disputed':
                    parts += ' [USER_DISPUTED]'
            out += parts
            if r[3] and r[4]:
                internal = any(se[0] == se2[0]
                               for se in r[3] for se2 in r[4])
                out += ('; SOURCE-INTERNAL CONFLICT' if internal
                        else '; CONFLICT')
            ep3 = self._read_ev_parts(r[3])
            ep4 = self._read_ev_parts(r[4])
            # Effective independent support: distinct corpus lineage
            # groups + unabsorbed url sources + typed sources. One
            # corpus lineage never manufactures MULTI_SOURCE.
            eff3 = ep3[1] + ep3[2] + ep3[3]
            eff4 = ep4[1] + ep4[2] + ep4[3]
            tier = ''
            if eff3 >= 2:
                tier = 'MULTI_SOURCE positive'
            if eff4 >= 2:
                tier = (tier + ', ' if tier else '') + \
                    'MULTI_SOURCE negative'
            if tier:
                out += '; ' + tier
            # A19: corpus-sourced evidence is marked DISTINCTLY.
            # SINGLE_CORPUS requires EVERY source on the side to be a
            # corpus source of one lineage (an absorbed same-publisher
            # fetched page does not make the side corpus-only).
            allp = all(self._corpus_lineage(se[0]) != '' for se in r[3])
            alln = all(self._corpus_lineage(se[0]) != '' for se in r[4])
            if r[3] and allp and ep3[2] == 1:
                out += ('; SINGLE_CORPUS positive (one corpus lineage, '
                        'map v' + self._lineage_map_version() +
                        ', not independent corroboration)')
            if r[4] and alln and ep4[2] == 1:
                out += ('; SINGLE_CORPUS negative (one corpus lineage, '
                        'map v' + self._lineage_map_version() +
                        ', not independent corroboration)')
            if len(r[3]) >= 2:
                out += '; positive evidence: ' + self._read_ev(r[3])
            if len(r[4]) >= 2:
                out += '; negative evidence: ' + self._read_ev(r[4])
            if self._read_eligible(r[3], r[4], r[5]):
                out += ('; SOURCE_DIVERSITY_THRESHOLD_MET positive'
                        ' evidence (not a fact)')
            if self._read_eligible(r[4], r[3], r[6]):
                out += ('; SOURCE_DIVERSITY_THRESHOLD_MET negative'
                        ' evidence (not a fact)')
            if r[5] == '' and r[6] == '' and not tier and \
                    not (r[3] and r[4]):
                out += '; UNVERIFIED'
            ids = []
            for se in r[3] + r[4]:
                if se[0] not in ids:
                    ids.append(se[0])
            if len(ids) >= 2:
                out += '; independence UNVERIFIED'
            if detail:
                for se in r[3]:
                    out += ('\n  ' + se[0] + ' (positive): "' + se[1] +
                            '" [pattern ' + se[2] + ']')
                for se in r[4]:
                    out += ('\n  ' + se[0] + ' (negative): "' + se[1] +
                            '" [pattern ' + se[2] + ']')
                if r[7]:
                    out += ('\n  approval history: ' +
                            ', '.join(he[0] + ' ' + he[1]
                                      for he in r[7]))
        if detail and self.url_srcs:
            for i, e in enumerate(self.url_srcs):
                out += ('\nurl-' + str(i + 1) + ' = ' +
                        self._url_disp(e[0]) + ' (fetched ' +
                        str(e[1]) + ' times)')
        if detail and self.corpus_srcs:
            for i, e in enumerate(self.corpus_srcs):
                out += ('\ncorpus-' + str(i + 1) + ' = ' + e +
                        ' (corpus lineage, map v' +
                        self._lineage_map_version() + ')')
        return out

    def _url_disp(self, norm):
        q = norm.find('?')
        return norm[:q] + '?(redacted)' if q >= 0 else norm

    def _read_hist(self, r, ev, pol):
        # A19: approval/revocation history, bounded at 20.
        r[7].append([ev, pol])
        if len(r[7]) > 20:
            r[7] = r[7][-20:]

    def _read_realign(self, s):
        # A19: alignments whose taught edge was dropped are
        # revoked, recorded in the history.
        for r in self.readings:
            if r[0] == s and (r[5] or r[6]):
                if r[5]:
                    self._read_hist(r, 'revoked', 'positive')
                if r[6]:
                    self._read_hist(r, 'revoked', 'negative')
                r[5] = ''
                r[6] = ''

    def _drop_rels(self, key):
        self.rels = [e for e in self.rels if e[0] != key]
        self._read_realign(key)
        if key in self.relset:
            self.relset[key] = {}
        ns = stripart(key)
        for p in self.relby:
            if ns in self.relby[p]:
                self.relby[p][ns] = []

    def _learn_rel(self, key, value):
        v = lower_ascii(value)
        got = False
        if v[:3] == 'in ' and len(v) > 3:
            self._add_rel(key, 'is-in', v[3:])
            got = True
        if (v[:2] == 'a ' and len(v) > 2) or (v[:3] == 'an ' and len(v) > 3):
            self._add_rel(key, 'is-a', v)
            got = True
        if v[:4] == 'has ' and len(v) > 4:
            self._add_rel(key, 'has', v[4:])
            got = True
        # A17: plural value shapes, matching the reader patterns.
        if v[:8] == 'are not ' and len(v) > 8:
            self._add_rel(key, 'not-is-a', v[8:])
            return False
        if v[:4] == 'are ' and len(v) > 4:
            self._add_rel(key, 'is-a', v[4:])
            got = True
        if v[:5] == 'have ' and len(v) > 5:
            self._add_rel(key, 'has', v[5:])
            got = True
        for p, pred in (('อยู่ ', 'is-in'), ('คือ ', 'means'),
                        ('หมายความว่า ', 'means'), ('เป็น ', 'is-a'),
                        ('มี ', 'has')):
            if v.startswith(p) and len(v) > len(p):
                self._add_rel(key, pred, v[len(p):])
                got = True
        v6 = lower_ascii(value[:6])
        v7 = lower_ascii(value[:7])
        if (v6 == 'not a ' and len(value) > 6) or \
                (v7 == 'not an ' and len(value) > 7) or \
                (lower_ascii(value[:4]) == 'not ' and len(value) > 4):
            self._add_rel(key, 'not-is-a', lower_ascii(value)[4:])
            return False
        if value.startswith('ไม่เป็น ') and len(value) > len('ไม่เป็น '):
            self._add_rel(key, 'not-is-a', value[len('ไม่เป็น '):])
            return False
        # A12: a value matching no recognized shape is a bare kind-of.
        if not got:
            self._add_rel(key, 'is-a', v)
            return True
        return False

    def _chain(self, start, pred, goal):
        g = stripart(goal)
        visited = set()
        queue = [(stripart(start), [])]
        qi = 0
        while qi < len(queue):
            node, path = queue[qi]
            qi += 1
            if node == g and path:
                return path
            if len(path) < 8 and node not in visited:
                visited.add(node)
                for s, o in self.relby.get(pred, {}).get(node, []):
                    queue.append((stripart(o), path + [[s, o]]))
        return None

    def _where_chain(self, start):
        node = stripart(start)
        path = []
        visited = set()
        while node not in visited and len(path) < 8:
            visited.add(node)
            found = None
            for e in self.relby.get('is-in', {}).get(node, []):
                if found is None:
                    found = e
            if found is None:
                break
            path.append(list(found))
            node = stripart(found[1])
        return path

    def _chain_fmt(self, path, pred):
        out = 'yes:'
        for s, o in path:
            if pred == 'is-in':
                out += ' ' + s + ' is in ' + o + ','
            if pred == 'is-a':
                out += ' ' + s + ' is ' + o + ','
        return out[:-1]

    def _chain_reply(self, x, pred, y):
        path = self._chain(x, pred, y)
        if path is None:
            return 'not that i know'
        return self._chain_fmt(path, pred)

    def _inherit(self, start, pred, goal):
        g = stripart(goal)
        npred = 'not-' + pred
        frontier = [(stripart(start), [])]
        visited = set()
        dist = 0
        verdict = ''
        pos = neg = None
        while frontier and dist <= 8 and verdict == '':
            nxt = []
            for node, path in frontier:
                if node in visited:
                    continue
                visited.add(node)
                if pos is None:
                    for e in self.relby.get(pred, {}).get(node, []):
                        if pos is None and stripart(e[1]) == g:
                            pos = (path, e)
                if neg is None:
                    for e in self.relby.get(npred, {}).get(node, []):
                        if neg is None and stripart(e[1]) == g:
                            neg = (path, e)
                if dist < 8:
                    for e in self.relby.get('is-a', {}).get(node, []):
                        ns = stripart(e[1])
                        if ns not in visited:
                            nxt.append((ns, path + [e]))
            if pos is not None and neg is not None:
                verdict = 'both'
            elif pos is not None:
                verdict = 'true'
            elif neg is not None:
                verdict = 'false'
            if verdict == '':
                frontier = nxt
                dist += 1
        if verdict == 'true':
            return [verdict, pos[0], pos[1], None, None]
        if verdict == 'false':
            return [verdict, neg[0], neg[1], None, None]
        if verdict == 'both':
            return [verdict, pos[0], pos[1], neg[0], neg[1]]
        return ['', None, None, None, None]

    def _pathfmt(self, path):
        return ''.join(s + ' is ' + o + ', ' for s, o in path)

    def _edgefmt(self, edge, pred, neg):
        return edge[0] + ' ' + (negphrase(pred) if neg else posphrase(pred)) + ' ' + edge[1]

    def _inherit_reply(self, x, pred, y):
        return self._verdict_reply(self._inherit(x, pred, y), pred, False)

    # A14 rule engine, mirroring _guard/_enum/_rule_prove/_derive/
    # _proof_* in agent/core.holy. Proofs are ('edge', path, edge, rel)
    # or ('rule', name, premise1, premise2, [subject, object], rel,
    # [guard kind, guard verdict, domain]). A14.1: rules declare a
    # domain; the guard checks each step's own subject through the
    # is-a engine - ok (chain proven), assume (explore mode only), or
    # blocked (strict unknown / negative / conflicting evidence).
    def _guard(self, subj, rule, gfail):
        gr = self._inherit(subj, 'is-a', rule[4])
        if gr[0] == 'true':
            return ('ok', gr)
        if gr[0] == '' and self.mode == 'explore':
            return ('assume', gr)
        gfail.append([rule[3], subj, rule[4], gr[0]])
        return ('', gr)

    def _enum(self, start, rel, depth, memo, gfail):
        mkey = stripart(start) + '|' + rel
        if mkey in memo:
            return memo[mkey]
        memo[mkey] = []
        cands = []
        seen = set()
        frontier = [(stripart(start), [])]
        visited = set()
        dist = 0
        while frontier and dist <= 8:
            nxt = []
            for node, path in frontier:
                if node in visited:
                    continue
                visited.add(node)
                for e in self.relby.get(rel, {}).get(node, []):
                    o = stripart(e[1])
                    if o not in seen:
                        seen.add(o)
                        cands.append(e[1])
                if dist < 8:
                    for e in self.relby.get('is-a', {}).get(node, []):
                        ns = stripart(e[1])
                        if ns not in visited:
                            nxt.append((ns, path + [e]))
            frontier = nxt
            dist += 1
        out = []
        for c in cands:
            r = self._inherit(start, rel, c)
            if r[0] == 'true':
                out.append([c, ('edge', r[1], r[2], rel)])
        if depth < RULECAP:
            for rule in RULES:
                ra, rb, rc, name = rule[0], rule[1], rule[2], rule[3]
                if rc == rel:
                    ys = self._enum(start, ra, depth + 1, memo, gfail)
                    if ys:
                        g = self._guard(start, rule, gfail)
                        if g[0]:
                            for yobj, yproof in ys:
                                for zobj, zproof in self._enum(yobj, rb, depth + 1, memo, gfail):
                                    o = stripart(zobj)
                                    if o not in seen:
                                        seen.add(o)
                                        out.append([zobj, ('rule', name, yproof, zproof,
                                                           [start, zobj], rel, (g[0], g[1], rule[4]))])
        memo[mkey] = out
        return out

    def _rule_prove(self, start, pred, goal, depth, memo, pseen, gfail):
        if depth >= RULECAP:
            return None
        if not any(rule[2] == pred for rule in RULES):
            return None
        pkey = stripart(start) + '|' + pred + '|' + stripart(goal)
        if pkey in pseen:
            return None
        pseen.add(pkey)
        for rule in RULES:
            ra, rb, rc, name = rule[0], rule[1], rule[2], rule[3]
            if rc == pred:
                ys = self._enum(start, ra, depth + 1, memo, gfail)
                if ys:
                    g = self._guard(start, rule, gfail)
                    if g[0]:
                        for yobj, yproof in ys:
                            r2 = self._inherit(yobj, rb, goal)
                            if r2[0] == 'true':
                                return ('rule', name, yproof,
                                        ('edge', r2[1], r2[2], rb), [start, goal],
                                        pred, (g[0], g[1], rule[4]))
                            if r2[0] == '':
                                p2 = self._rule_prove(yobj, rb, goal, depth + 1,
                                                      memo, pseen, gfail)
                                if p2 is not None:
                                    return ('rule', name, yproof, p2,
                                            [start, goal], pred, (g[0], g[1], rule[4]))
        return None

    def _derive(self, x, pred, y):
        r = self._inherit(x, pred, y)
        v = r[0]
        if v in ('true', 'both'):
            return [v, r, None, None]
        gfail = []
        p = self._rule_prove(x, pred, y, 0, {}, set(), gfail)
        if p is None:
            return [v, r, None, gfail]
        if v == 'false':
            return ['rule-both', r, p, None]
        return ['rule', None, p, None]

    def _proof_text(self, proof):
        if proof[0] == 'edge':
            return self._pathfmt(proof[1]) + self._edgefmt(proof[2], proof[3], False)
        return self._edgefmt(proof[4], proof[5], False)

    def _proof_steps(self, proof, steps, done, assum):
        t = self._proof_text(proof)
        if proof[0] == 'edge':
            return t
        t1 = self._proof_steps(proof[2], steps, done, assum)
        t2 = self._proof_steps(proof[3], steps, done, assum)
        if t not in done:
            done.add(t)
            line = t1 + ' + ' + t2 + ' => ' + t + ' [rule ' + proof[1]
            if proof[6][0] == 'ok':
                line += ('; domain: ' + self._pathfmt(proof[6][1][1]) +
                         self._edgefmt(proof[6][1][2], 'is-a', False))
            line += ']'
            steps.append('(' + str(len(steps) + 1) + ') ' + line)
            if proof[6][0] == 'assume':
                assum.append([proof[4][0], proof[6][2], len(steps), proof[1]])
        return t

    def _derive_render(self, x, pred, y, d):
        if d[0] in ('rule', 'rule-both'):
            steps = []
            assum = []
            self._proof_steps(d[2], steps, set(), assum)
            if d[0] == 'rule':
                if assum:
                    out = ('yes, on ' + str(len(assum)) + ' assumption' +
                           ('s' if len(assum) > 1 else '') + ': ')
                else:
                    out = 'yes: '
                out += x + ' ' + posphrase(pred) + ' ' + y + '. reasoning:'
            else:
                r = d[1]
                out = ('i was taught ' + self._pathfmt(r[1]) +
                       self._edgefmt(r[2], pred, True) +
                       ', but the rules derive ' + x + ' ' + posphrase(pred) +
                       ' ' + y + ' - i cannot say which is true. reasoning:')
            out += ''.join('\n' + s for s in steps)
            if assum:
                merged = []
                mseen = {}
                for a in assum:
                    mk = a[0] + '|' + a[1]
                    if mk in mseen:
                        merged[mseen[mk]][2] += ', ' + str(a[2])
                    else:
                        mseen[mk] = len(merged)
                        merged.append([a[0], a[1], str(a[2])])
                labels = 'abcdefghijklmnopqrstuvwxyz'
                out += '\nassumptions:'
                for i, m in enumerate(merged):
                    out += ('\n(' + labels[i] + ') ' + m[0] + ' is a ' + m[1] +
                            ' - assumed at step ' + m[2] + ', unverified')
                if not self._hyp_record(self._hyp_q(x, pred, y), assum):
                    out += ('\n(hypothesis list full - teach or forget '
                            'hypotheses to free space)')
            return out
        if d[0] == '' and d[3]:
            f = d[3][0]
            if f[3] == '':
                return ('not that i know - rule ' + f[0] + ' applies only to ' +
                        f[2] + 's, and i do not know whether ' + f[1] +
                        ' is a ' + f[2])
            if f[3] == 'false':
                return ('not that i know - rule ' + f[0] + ' applies only to ' +
                        f[2] + 's, and ' + f[1] + ' is not a ' + f[2])
            return ('not that i know - rule ' + f[0] + ' applies only to ' +
                    f[2] + 's, and i was taught both that ' + f[1] +
                    ' is and is not a ' + f[2])
        return self._verdict_reply(d[1], pred, False)

    def _derive_reply(self, x, pred, y):
        return self._derive_render(x, pred, y, self._derive(x, pred, y))

    def _verdict_reply(self, r, pred, isa):
        v = r[0]
        if v == '':
            return 'not that i know'
        if v == 'both':
            return ('i was taught both: ' + self._pathfmt(r[1]) +
                    self._edgefmt(r[2], pred, False) + ' and ' +
                    self._pathfmt(r[3]) + self._edgefmt(r[4], pred, True) +
                    ' - i cannot say which is true')
        if v == 'true':
            if isa:
                return self._chain_fmt(r[1] + [r[2]], 'is-a')
            if not r[1]:
                return 'yes: ' + self._edgefmt(r[2], pred, False) + ' (taught)'
            return 'yes: ' + self._pathfmt(r[1]) + self._edgefmt(r[2], pred, False)
        if not r[1]:
            return 'no: ' + self._edgefmt(r[2], pred, True) + ' (taught)'
        return 'no: ' + self._pathfmt(r[1]) + self._edgefmt(r[2], pred, True)

    def _isa_reply(self, x, y):
        return self._verdict_reply(self._inherit(x, 'is-a', y), 'is-a', True)

    def _verb_q(self, rest):
        for marker, pred in VERBQ:
            k = rest.find(marker)
            if k > 0 and k + len(marker) < len(rest):
                return self._derive_reply(rest[:k], pred, rest[k + len(marker):])
        return 'i do not understand'

    def _can_q(self, rest):
        ws = words(rest)
        if len(ws) < 2:
            return 'i do not understand'
        x = ws[0]
        i = 1
        blocked = None
        bx = by = ''
        while i < len(ws):
            y = rest[len(x) + 1:]
            d = self._derive(x, 'can', y)
            if d[0] != '':
                return self._derive_render(x, 'can', y, d)
            if blocked is None and d[3]:
                blocked = d
                bx, by = x, y
            x = x + ' ' + ws[i]
            i += 1
        if blocked is not None:
            return self._derive_render(bx, 'can', by, blocked)
        return 'not that i know'

    def _passive_reply(self, rest3):
        for marker, pred in VERBP:
            k = rest3.find(marker)
            if k > 0 and k + len(marker) < len(rest3):
                return self._derive_reply(rest3[k + len(marker):], pred, rest3[:k])
        return None

    def _verb_teach_parse(self, mrest):
        for marker, pred, neg in VERBT:
            k = mrest.find(marker)
            if k > 0 and k + len(marker) < len(mrest):
                return (k, pred, neg, k + len(marker))
        return None

    def _contra_warn(self, key, pred, obj, neg):
        opp = pred if neg else 'not-' + pred
        if obj in self.relset.get(key, {}).get(opp, {}):
            return (' (warning: this contradicts what you taught me earlier'
                    ' - i hold both and will say so when asked)')
        return ''

    def _isa_contra_warn(self, key, value):
        lv = lower_ascii(value)
        obj, opp = lv, 'not-is-a'
        if lv[:4] == 'not ':
            obj, opp = lv[4:], 'is-a'
        if lv.startswith('ไม่เป็น '):
            obj, opp = lv[len('ไม่เป็น '):], 'is-a'
        if lv.startswith('เป็น '):
            obj, opp = lv[len('เป็น '):], 'not-is-a'
        if obj in self.relset.get(key, {}).get(opp, {}):
            return (' (warning: this contradicts what you taught me earlier'
                    ' - i hold both and will say so when asked)')
        return ''

    def _teach_verb(self, key, pred, obj, neg):
        self.topic = key
        newkey = key not in self.order
        ph = negphrase(pred) if neg else posphrase(pred)
        val = ph + ' ' + obj
        dup = key in self.facts and val in self.facts[key]
        self._add_rel(key, 'not-' + pred if neg else pred, obj)
        if not dup:
            if newkey:
                self.facts[key] = []
                self.order.append(key)
            self.facts[key].append(val)
            self._cooc_add(key, val)
            self._slog('taught', key)
        if dup:
            return 'i already know that ' + key + ' ' + val
        reply = 'remembered ' + key + ' ' + val
        if not newkey:
            reply = 'added: ' + key + ' ' + val
        return reply + self._contra_warn(key, pred, obj, neg)

    def _is_bare_reply(self, rest3):
        ws = words(rest3)
        if len(ws) < 2:
            return 'i do not understand'
        x = ws[0]
        i = 1
        while i < len(ws):
            y = rest3[len(x) + 1:]
            r = self._inherit(x, 'is-a', y)
            if r[0] != '':
                return self._isa_reply(x, y)
            x = x + ' ' + ws[i]
            i += 1
        return 'not that i know'

    def _means_check(self, x, y, sep):
        if y in self.relset.get(x, {}).get('means', {}):
            return 'yes: ' + x + sep + y
        return 'not that i know'

    def _slog(self, kind, key):
        self.session.append([kind, key])
        if len(self.session) > 10:
            self.session = self.session[-10:]

    def _where_reply(self, x, sep):
        path = self._where_chain(x)
        if not path:
            return self._recall(x)
        return ', '.join(s + sep + o for s, o in path)

    def _mean_reply(self, x, sep):
        defs = [e[2] for e in BUILTIN_RELS if e[0] == x]
        defs += [e[2] for e in self.rels if e[0] == x and e[1] == 'means']
        if defs:
            if self.lang == 'th':
                return x + sep + join_th(defs)
            return x + sep + join_values(defs)
        return self._recall(x)

    def respond(self, line):
        text = normalize(line)
        qmark = False
        if text and text[-1] == '?':
            qmark = True
            text = text[:-1]
        if text and text[-1] == '.':
            text = text[:-1]
        m = lower_ascii(text)
        self.lang = 'th' if thai_line(text) else 'en'
        if self.pending is not None:
            handled, reply = self._pending_reply(m)
            if handled:
                return reply
        if m == 'help':
            return HELP
        if m == 'list':
            return self._list_reply()
        if m == 'notes':
            return self._notes_reply()
        if m == 'clear notes':
            self.notes = []
            return 'notes cleared'
        if m == 'mode':
            if self.mode == 'explore':
                return ('explore mode: compositional rules may fire on '
                        'unverified domains; conclusions list their assumptions '
                        'and assumptions never become facts')
            return ("strict mode (the default): compositional rules need "
                    "verified domains; 'mode explore' allows conditional conclusions")
        if m == 'mode explore':
            self.mode = 'explore'
            return ('explore mode: compositional rules may fire on unverified '
                    'domains; conclusions list their assumptions (this session only)')
        if m == 'mode strict':
            self.mode = 'strict'
            return ('strict mode: compositional rules need verified domains '
                    '(this session only)')
        if m == 'hypotheses':
            return self._hyp_reply(False)
        if m == 'hypotheses detail':
            return self._hyp_reply(True)
        if m == 'clear hypotheses':
            self.hypotheses = []
            self.hyp_retired = []
            return 'hypotheses cleared'
        if m[:18] == 'forget hypothesis ':
            rest = m[18:]
            for sep in (' is a ', ' is an '):
                k = rest.find(sep)
                if k > 0 and k + len(sep) < len(rest):
                    subj, domain = rest[:k], rest[k + len(sep):]
                    if self._hyp_find(subj, domain) >= 0:
                        self._hyp_retire(subj, domain, 'forgotten')
                        return 'forgotten: hypothesis ' + subj + sep + domain
                    return "no such hypothesis - 'hypotheses' lists the open ones"
            return 'forget hypothesis <thing> is a <kind>'
        # A16 reader: ingest text as data (never executed), inspect
        # and manage read candidates. 'forget reading' precedes the
        # generic forget route.
        if m == 'readings':
            return self._readings_reply('', False)
        if m == 'readings detail':
            return self._readings_reply('', True)
        if m[:15] == 'readings about ' and len(m) > 15:
            return self._readings_reply(m[15:], False)
        if m == 'clear readings':
            self.readings = []
            self.read_src = {}
            self.url_srcs = []
            self.corpus_srcs = []
            return 'readings cleared'
        if m[:15] == 'forget reading ' and len(m) > 15:
            fr = self._read_extract(m[15:])
            if fr is not None:
                ri3 = self._read_find(fr[0], fr[1], fr[2])
                if ri3 >= 0:
                    r = self.readings.pop(ri3)
                    return ('forgotten: reading ' + r[0] + ' | ' + r[1] +
                            ' | ' + r[2])
                return "no such reading - 'readings' lists them"
            return 'forget reading <thing> is a <kind>'
        if m[:12] == 'read corpus ' and len(text) > 12:
            return self._read_corpus(text[12:])
        if m[:9] == 'read url ' and len(text) > 9:
            return self._read_url(text[9:])
        if m[:5] == 'read ' and len(text) > 5:
            return self._read_text(text[5:])
        if m[:5] == 'note ' and len(text) > 5:
            self.notes.append(text[5:])
            return 'noted'
        if m == 'what about it':
            if self.topic is None:
                return 'i have no topic yet'
            return self._recall(self.topic)
        if m in ('hello', 'hi', 'hey'):
            return 'hello - teach me something with: remember <thing> is <fact>'
        if m == 'how are you':
            return 'i am a pattern matcher, not a person - but the patterns are working'
        if m in ('thanks', 'thank you'):
            return 'noted - i do not feel it, but the fact store appreciates the exercise'
        if m in ('bye', 'goodbye'):
            return 'type quit to leave, or keep teaching me'
        if m == 'สวัสดี':
            return 'สวัสดี - สอนผมได้ด้วย: remember <thing> is <fact>'
        if m == 'ขอบคุณ':
            return 'ยินดี - ผมไม่ได้รู้สึก แค่จับคู่รูปแบบ'
        if m in ('what else', 'anything else'):
            if self.topic is None:
                return 'i have no topic yet'
            facts = self.facts[self.topic]
            if len(facts) <= 1:
                return 'that is all i know about ' + self.topic
            return 'about ' + self.topic + ': ' + join_values(facts[1:])
        if m[:4] == 'and ' and len(m) > 4:
            return self._recall(m[4:])
        if m[:7] == 'how is ':
            return self._open_reply(m[7:])
        if m[:7] == 'why is ':
            return self._open_reply(m[7:])
        if m[:8] == 'when is ':
            return self._open_reply(m[8:])
        if m[:10] == 'how about ':
            return self._open_reply(m[10:])
        if m[:25] == 'tell me everything about ':
            return self._open_reply(m[25:])
        pc = self._pron_clarify(m, qmark)
        if pc is not None:
            return pc
        p = 'เกี่ยวกับ '
        if m.find(p) == 0:
            return self._open_reply(m[len(p):])
        k = m.find(' คืออะไร')
        if k > 0 and k + len(' คืออะไร') == len(m):
            return self._recall(m[:k])
        if m == 'forget it':
            if self.topic is None:
                return 'i have no topic yet'
            return self._forget(self.topic)
        if m in ('what do you know', 'how many things do you know',
                 'what have you learned'):
            return self._know_reply()
        if m in ('what did you forget', 'what have you forgotten'):
            return self._forgotten_reply()
        if m in ('what did we talk about', 'what happened this session'):
            return self._session_reply()
        if m[:23] == 'what do you know about ':
            return self._about_reply(m[23:])
        if m[:9] == 'remember ':
            rest = text[9:]
            mrest = m[9:]
            k = mrest.find(' is also ')
            if k > 0 and k + 9 < len(mrest):
                return self._teach_also(mrest[:k], rest[k + 9:])
            k = mrest.find(' is ')
            if k > 0 and k + 4 < len(mrest):
                if mrest[:k] in self.order and kind_value(mrest[k + 4:]):
                    return self._teach_also(mrest[:k], rest[k + 4:])
                return self._teach(mrest[:k], rest[k + 4:])
            k = mrest.find(' has ')
            if k > 0 and k + 5 < len(mrest):
                return unteach_is(self._teach_also(mrest[:k], rest[k + 1:]), 'has')
            # A17: plural teach forms mirroring the singular routes.
            k = mrest.find(' do not have ')
            if k > 0 and k + 13 < len(mrest):
                return self._teach_verb(mrest[:k], 'has', mrest[k + 13:], True)
            k = mrest.find(' does not have ')
            if k > 0 and k + 15 < len(mrest):
                return self._teach_verb(mrest[:k], 'has', mrest[k + 15:], True)
            k = mrest.find(' are not ')
            if k > 0 and k + 9 < len(mrest):
                return unteach_is(self._teach_also(mrest[:k], rest[k + 1:]), 'are not')
            k = mrest.find(' have ')
            if k > 0 and k + 6 < len(mrest):
                return unteach_is(self._teach_also(mrest[:k], rest[k + 1:]), 'have')
            k = mrest.find(' are ')
            if k > 0 and k + 5 < len(mrest):
                return unteach_is(self._teach_also(mrest[:k], rest[k + 1:]), 'are')
            k = mrest.find(' อยู่ ')
            if k > 0 and k + len(' อยู่ ') < len(mrest):
                return unteach_is(self._teach_also(mrest[:k], rest[k + 1:]), 'อยู่')
            k = mrest.find(' คือ ')
            if k > 0 and k + len(' คือ ') < len(mrest):
                return unteach_is(self._teach_also(mrest[:k], rest[k + 1:]), 'คือ')
            k = mrest.find(' เป็น ')
            if k > 0 and k + len(' เป็น ') < len(mrest):
                return unteach_is(self._teach_also(mrest[:k], rest[k + 1:]), 'เป็น')
            k = mrest.find(' ไม่เป็น ')
            if k > 0 and k + len(' ไม่เป็น ') < len(mrest):
                return unteach_is(self._teach_also(mrest[:k], rest[k + 1:]), 'ไม่เป็น')
            vt = self._verb_teach_parse(mrest)
            if vt is not None:
                return self._teach_verb(mrest[:vt[0]], vt[1], mrest[vt[3]:], vt[2])
            k = mrest.find(' มี ')
            if k > 0 and k + len(' มี ') < len(mrest):
                return unteach_is(self._teach_also(mrest[:k], rest[k + 1:]), 'มี')
            return 'i do not understand'
        if m[:10] == 'what does ' and len(m) > 15 and m[-5:] == ' mean':
            return self._mean_reply(m[10:-5], ' means ')
        if m[:3] == 'is ':
            rest3 = m[3:]
            pv = self._passive_reply(rest3)
            if pv is not None:
                return pv
            k = rest3.find(' in ')
            if k > 0:
                return self._chain_reply(rest3[:k], 'is-in', rest3[k + 4:])
            k = rest3.find(' an ')
            if k > 0:
                return self._isa_reply(rest3[:k], rest3[k + 4:])
            k = rest3.find(' a ')
            if k > 0:
                return self._isa_reply(rest3[:k], rest3[k + 3:])
            return self._is_bare_reply(rest3)
        k = m.find(' หมายความว่าอะไร')
        if k > 0 and k + len(' หมายความว่าอะไร') == len(m):
            return self._mean_reply(m[:k], ' คือ ')
        k = m.find(' อยู่ไหน')
        if k > 0 and k + len(' อยู่ไหน') == len(m):
            return self._where_reply(m[:k], ' อยู่ ')
        if m[:8] == 'what is ':
            return self._recall(m[8:])
        if m[:12] == 'do you know ':
            return self._recall(m[12:])
        if m[:15] == 'tell me about ':
            return self._recall(m[15:])
        if m[:7] == 'who is ':
            return self._recall(m[7:])
        if m[:9] == 'where is ':
            return self._where_reply(m[9:], ' is in ')
        if m[:5] == 'does ' and len(m) > 5:
            return self._verb_q(m[5:])
        if m[:3] == 'do ' and len(m) > 3:
            return self._verb_q(m[3:])
        if m[:4] == 'can ' and len(m) > 4:
            return self._can_q(m[4:])
        if m[:7] == 'forget ':
            return self._forget(m[7:])
        if m[:4] == 'say ' and len(text) > 4:
            return text[4:]
        if m[:4] == 'no, ':
            rest = text[4:]
            mrest = m[4:]
            k = mrest.find(' is ')
            if k > 0 and k + 4 < len(mrest):
                key = mrest[:k]
                resolved = self._resolve(key)
                if resolved is not None:
                    key = resolved
                return self._teach(key, rest[k + 4:])
            cr = self._correct_thai(rest, mrest)
            if cr is not None:
                return cr
            return 'i do not understand'
        q = m
        isq = False
        for suf in (' หรือไม่', 'หรือไม่', ' ไหม', 'ไหม'):
            if len(q) > len(suf) and q.endswith(suf):
                q = q[:-len(suf)]
                isq = True
        if not isq and qmark:
            isq = True
        if isq:
            k = q.find(' เป็น ')
            if k < 0:
                k = q.find('เป็น')
                d = len('เป็น')
            else:
                d = len(' เป็น ')
            if k > 0 and k + d < len(q):
                return self._isa_reply(q[:k], q[k + d:])
            k = q.find(' คือ ')
            if k < 0:
                k = q.find('คือ')
                d = len('คือ')
            else:
                d = len(' คือ ')
            if k > 0 and k + d < len(q):
                return self._means_check(q[:k], q[k + d:], ' คือ ')
        means_p = None
        for p in (' means ', ' หมายความว่า ', ' คือ '):
            k = m.find(p)
            if k > 0:
                means_p = p
                break
        if means_p is not None and k + len(means_p) < len(m):
            phrase = m[:k]
            target = m[k + len(means_p):]
            if phrase == target:
                return 'i do not understand'
            if qmark:
                return self._means_check(phrase, target, means_p)
            self._add_rel(phrase, 'means', target)
            if target in self.facts:
                self.aliases[phrase] = target
            if self.lang == 'th':
                return 'เข้าใจแล้ว' + self._particle() + ' ' + phrase + means_p + target
            return 'ok, ' + phrase + means_p + target
        if self.lang == 'th':
            return 'ไม่เข้าใจ' + self._particle()
        return 'i do not understand'

    def _pending_reply(self, m):
        p = self.pending
        if m == 'yes':
            if len(p['cands']) == 1:
                self.pending = None
                return True, self._recall(p['cands'][0])
            return True, 'please say which one'
        if m == 'no':
            self.pending = None
            return True, 'ok'
        for cand in p['cands']:
            if cand == m:
                self.pending = None
                return True, self._recall(cand)
        self.pending = None
        return False, ''

    def _resolve(self, key):
        if key in self.facts:
            return key
        if key in self.aliases:
            target = self.aliases[key]
            if target in self.facts:
                return target
            return None
        return None

    def _open_reply(self, thing):
        resolved = self._resolve(thing)
        if resolved is not None:
            self.topic = resolved
            return 'all i know about ' + resolved + ' is ' + \
                join_values(self.facts[resolved])
        return self._recall(thing)

    def _candidates(self, phrase):
        ws = words(phrase)
        cands = []
        keys = []
        if ws:
            for k in self.order:
                if k != phrase and \
                        all(any(wmatch(w, kw) for kw in words(k)) for w in ws):
                    cands.append(k)
                    keys.append(k)
            for a, target in self.aliases.items():
                if target in self.facts and a != phrase and \
                        all(any(wmatch(w, aw) for aw in words(a)) for w in ws):
                    cands.append(a)
                    keys.append(target)
        return cands, keys

    def _teach(self, key, value):
        self.topic = key
        if key in self.facts:
            for v in self.facts[key]:
                self._cooc_remove(key, v)
        self.facts[key] = [value]
        self._drop_rels(key)
        bare = self._learn_rel(key, value)
        self._cooc_add(key, value)
        self._slog('taught', key)
        suffix = ' (filed as a kind-of)' if bare else ''
        tsuffix = ' (บันทึกเป็นชนิด)' if bare else ''
        if key in self.order:
            if self.lang == 'th':
                return 'แก้ไว้แล้ว' + self._particle() + ' ' + key + ' คือ ' + value + tsuffix
            return 'updated ' + key + ' is ' + value + suffix
        self.order.append(key)
        if self.lang == 'th':
            return 'จำไว้แล้ว' + self._particle() + ' ' + key + ' คือ ' + value + tsuffix
        return 'remembered ' + key + ' is ' + value + suffix

    THAI_PRON = ('มัน', 'เขา', 'เธอ', 'อันนี้', 'อันนั้น', 'ตัวนี้', 'ตัวนั้น', 'ตัว นี้',
                 'ตัว นั้น', 'คนนี้', 'คนนั้น', 'คน นี้', 'คน นั้น', 'ที่นี่', 'ที่นั่น',
                 'ที่ นี่', 'ที่ นั่น', 'นี่', 'นั่น', 'โน่น')

    def _pron_subject(self, m, qmark):
        for suf in (' อยู่ไหน', ' คืออะไร', ' หมายความว่าอะไร'):
            k = m.find(suf)
            if k > 0 and k + len(suf) == len(m):
                return m[:k]
        p = 'เกี่ยวกับ '
        if m.find(p) == 0 and len(m) > len(p):
            return m[len(p):]
        q = m
        isq = False
        for suf in (' หรือไม่', 'หรือไม่', ' ไหม', 'ไหม'):
            if len(q) > len(suf) and q[len(q) - len(suf):] == suf:
                q = q[:len(q) - len(suf)]
                isq = True
        if not isq and qmark:
            isq = True
        if isq:
            k = q.find(' เป็น ')
            if k < 0:
                k = q.find('เป็น')
                d = len('เป็น')
            else:
                d = len(' เป็น ')
            if k > 0 and k + d < len(q):
                return q[:k]
            k = q.find(' คือ ')
            if k < 0:
                k = q.find('คือ')
                d = len('คือ')
            else:
                d = len(' คือ ')
            if k > 0 and k + d < len(q):
                return q[:k]
        return None

    def _pron_clarify(self, m, qmark):
        subj = self._pron_subject(m, qmark)
        if subj is None or subj not in self.THAI_PRON:
            return None
        if self._resolve(subj) is not None:
            return None
        t = self.topic
        if t is not None and t in self.facts:
            return 'did you mean ' + t + '? clarify by saying the name'
        return 'clarify: which thing do you mean by ' + subj + '? say its name'

    def _correct_thai(self, rest, mrest):
        for word in ('อยู่', 'คือ', 'เป็น', 'มี'):
            mk = ' ' + word + ' '
            k = mrest.find(mk)
            if k > 0 and k + len(mk) < len(mrest):
                key = mrest[:k]
                resolved = self._resolve(key)
                if resolved is None:
                    return 'nothing to correct: i do not know ' + key
                newval = rest[k + 1:]
                prefix = word + ' '
                kept, replaced, placed = [], 0, False
                for v in self.facts[resolved]:
                    if v.startswith(prefix):
                        replaced += 1
                        self._cooc_remove(resolved, v)
                        if not placed:
                            kept.append(newval)
                            placed = True
                    else:
                        kept.append(v)
                if replaced == 0:
                    return 'nothing to correct: ' + resolved + ' has no ' + word + ' fact'
                self.facts[resolved] = kept
                self._drop_rels(resolved)
                for v in kept:
                    self._learn_rel(resolved, v)
                self._cooc_add(resolved, newval)
                self.topic = resolved
                self._slog('taught', resolved)
                if replaced > 1:
                    return ('updated ' + resolved + ' ' + newval + ' (replaced ' +
                            str(replaced) + ' earlier ' + word + ' facts)')
                return 'updated ' + resolved + ' ' + newval
        return None

    def _teach_also(self, key, value):
        self.topic = key
        bare = self._learn_rel(key, value)
        suffix = ' (filed as a kind-of)' if bare else ''
        tsuffix = ' (บันทึกเป็นชนิด)' if bare else ''
        th = self.lang == 'th'
        if key not in self.facts:
            self.facts[key] = [value]
            self.order.append(key)
            self._cooc_add(key, value)
            self._slog('taught', key)
            if th:
                return 'จำไว้แล้ว' + self._particle() + ' ' + key + ' คือ ' + value + tsuffix
            return 'remembered ' + key + ' is ' + value + suffix
        if value in self.facts[key]:
            if th:
                return 'รู้อยู่แล้ว' + self._particle() + ' ' + key + ' คือ ' + value + tsuffix
            return 'i already know that ' + key + ' is ' + value + suffix
        self.facts[key].append(value)
        self._cooc_add(key, value)
        self._slog('taught', key)
        if th:
            return ('เพิ่มไว้แล้ว' + self._particle() + ' ' + key + ' คือ ' + value +
                    tsuffix + self._isa_contra_warn(key, value))
        return ('added: ' + key + ' is ' + value + suffix +
                self._isa_contra_warn(key, value))

    def _values_glue(self, values):
        plain = [v for v in values if not relvalue(v)]
        relv = [v for v in values if relvalue(v)]
        if not relv:
            return ' is ' + join_values(values)
        if not plain:
            return ' ' + join_values(relv)
        return ' is ' + join_values(plain) + ' and ' + join_values(relv)

    def _values_glue_th(self, values):
        plain = [_th_val(v) for v in values if not relvalue(v)]
        relv = [v for v in values if relvalue(v)]
        if not relv:
            return ' คือ ' + join_th(plain)
        if not plain:
            return ' ' + join_th(relv)
        return ' คือ ' + join_th(plain) + ' และ ' + join_th(relv)

    def _recall(self, asked):
        key = self._resolve(asked)
        if key is not None:
            self.topic = key
            self._slog('asked', key)
            if self.lang == 'th':
                return 'รู้' + self._particle() + ' ' + key + self._values_glue_th(self.facts[key])
            return 'i know ' + key + self._values_glue(self.facts[key])
        cands, keys = self._candidates(asked)
        if len(cands) > 1:
            awords = cwords(asked)
            scored = sorted(range(len(cands)),
                            key=lambda i: -self._usage_score(cands[i], awords))
            cands = [cands[i] for i in scored]
            keys = [keys[i] for i in scored]
        if 0 < len(cands) <= 3:
            self.pending = {'cands': cands, 'keys': keys}
            if self.lang == 'th':
                return 'หมายถึง ' + ', '.join(cands) + ' ใช่ไหม' + self._particle() + '?'
            return 'did you mean ' + ', '.join(cands) + '?'
        if len(cands) > 3:
            if self.lang == 'th':
                return 'ไม่รู้จัก' + self._particle() + ' ' + asked
            return 'i do not know ' + asked
        return self._usage_reply(asked)

    def _forget(self, key):
        if key not in self.facts:
            if self.lang == 'th':
                return 'ไม่รู้จัก' + self._particle() + ' ' + key
            return 'i do not know ' + key
        vals = self.facts[key]
        del self.facts[key]
        self.order.remove(key)
        self.aliases = {a: t for a, t in self.aliases.items() if t != key}
        self._drop_rels(key)
        for v in vals:
            self._cooc_remove(key, v)
        if self.topic == key:
            self.topic = None
        self.forgotten.append(key)
        if len(self.forgotten) > 20:
            self.forgotten = self.forgotten[-20:]
        self._slog('forgot', key)
        if self.lang == 'th':
            return 'ลืมแล้ว' + self._particle() + ' ' + key
        return 'forgot ' + key

    def _list_reply(self):
        n = len(self.order)
        th = self.lang == 'th'
        if n == 0:
            if th:
                return 'ยังไม่รู้อะไรเลย' + self._particle()
            return 'i know nothing yet'
        if n > 50:
            if th:
                return ('รู้ ' + str(n) + ' อย่าง' + self._particle() + ': ' +
                        ', '.join(self.order[:50]) + ' และอีก ' + str(n - 50) + ' อย่าง')
            return ('i know ' + str(n) + ' things: ' +
                    ', '.join(self.order[:50]) + ', and ' + str(n - 50) + ' more')
        joined = ', '.join(self.order)
        if n == 1:
            if th:
                return 'รู้ 1 อย่าง' + self._particle() + ': ' + joined
            return 'i know 1 thing: ' + joined
        if th:
            return 'รู้ ' + str(n) + ' อย่าง' + self._particle() + ': ' + joined
        return 'i know ' + str(n) + ' things: ' + joined

    def _know_reply(self):
        n = len(self.order)
        if n == 0:
            return 'i know nothing yet'
        if n <= 5:
            return self._list_reply()
        return ('i know ' + str(n) + ' things; most recently: ' +
                join_values(self.order[-5:]))

    def _forgotten_reply(self):
        if not self.forgotten:
            return 'i have not forgotten anything since i started keeping track'
        return 'i forgot ' + join_values(self.forgotten) + ' (i only keep the last 20)'

    def _session_reply(self):
        if not self.session:
            return 'nothing has happened yet this session'
        out = ''
        for kind, key in self.session:
            if kind == 'asked':
                out += '; asked about ' + key
            else:
                out += '; ' + kind + ' ' + key
        return 'this session: ' + out[2:]

    def _value_words(self, key):
        out = []
        for v in self.facts[key]:
            for w in words(lower_ascii(v)):
                if w not in out:
                    out.append(w)
        return out

    def _about_reply(self, asked):
        key = self._resolve(asked)
        if key is None:
            return 'i do not know ' + asked
        self.topic = key
        reply = 'i know ' + key + ' is ' + join_values(self.facts[key])
        words = self._value_words(key)
        for k in self.order:
            if k == key:
                continue
            kwords = self._value_words(k)
            if any((len(w) >= 3 or nonascii(w)) and w not in STOP and
                   any(wmatch(w, kw) for kw in kwords) for w in words):
                reply += '; also ' + k + ' is ' + join_values(self.facts[k])
        return reply

    def _notes_reply(self):
        n = len(self.notes)
        if n == 0:
            return 'no notes yet'
        return '; '.join('note ' + str(i + 1) + ': ' + note
                         for i, note in enumerate(self.notes))


rng = random.Random(20261121)

KEYS = ['paris', 'milo', '曼谷', 'ไทย', 'café', 'x', 'my cat', 'a=b',
        'Tokyo', 'the answer', 'z', 'felix', 'c', 'แมวcat', 'red car']
# Overlapping content words across values exercise association recall.
VALUES = ['nice', 'a cat', 'a big cat', 'likes fish', 'a dog', 'blue fish',
          'ประเทศไทย', 'คนไทย', 'เมืองใหญ่', 'ไทยแลนด์', '42',
          'a City in France', 'ไม่รู้', 'x is y', 'blue green',
          'nothing much']
GARBAGE = ['', '   ', 'xyzzy', 'remember', 'remember x', 'remember is y',
           'what', 'what is', 'what is ', 'forget', 'say', 'say ',
           'remember x is', 'REMEMBER x IS ', 'hello there', '?', '.',
           'note', 'what do you know about', 'who is', 'where is',
           'means', 'x means', 'means y', 'x means x', 'remember x is also',
           'no,', 'no, x', 'no x is y']
ALIASES = ['do you know', 'tell me about', 'who is', 'where is']
# A8: pleasantries, open questions (EN+TH), topic chains.
PLEASANTRIES = ['hello', 'hi', 'hey', 'how are you', 'thanks', 'thank you',
                'bye', 'goodbye', 'สวัสดี', 'ขอบคุณ']
CHAINS = ['what else', 'anything else']


def a8_line():
    r = rng.random()
    if r < 0.20:
        return mangle(rng.choice(PLEASANTRIES[:8]))
    if r < 0.35:
        return rng.choice(PLEASANTRIES[8:])
    if r < 0.60:
        pat = rng.choice(['how is', 'why is', 'when is', 'how about',
                          'tell me everything about'])
        return mangle(pat) + ' ' + mangle(rng.choice(KEYS + MISSES))
    if r < 0.75:
        if rng.random() < 0.5:
            return 'เกี่ยวกับ ' + rng.choice(KEYS + MISSES)
        return rng.choice(KEYS + MISSES) + ' คืออะไร'
    if r < 0.90:
        return mangle('and') + ' ' + mangle(rng.choice(KEYS + MISSES))
    return mangle(rng.choice(CHAINS))
# Relation pools for the A9 inference lines.
PLACES = ['paris', 'france', 'europe', 'tokyo', 'japan', 'asia',
          'bangkok', 'thailand', 'garden']
KINDS = ['animal', 'mammal', 'cat', 'dog', 'bird', 'fish', 'pet']


def a9_line():
    r = rng.random()
    if r < 0.18:
        return (mangle('remember') + ' ' + rng.choice(PLACES) + ' ' +
                mangle('is in') + ' ' + rng.choice(PLACES))
    if r < 0.34:
        return (mangle('remember') + ' ' + rng.choice(KINDS) + ' ' +
                mangle('is') + ' ' + rng.choice(['a', 'an']) + ' ' +
                rng.choice(KINDS))
    if r < 0.44:
        return (mangle('remember') + ' ' + rng.choice(KINDS) + ' ' +
                mangle('has') + ' ' + rng.choice(VALUES))
    if r < 0.52:
        return (mangle('remember') + ' ' + rng.choice(KEYS + PLACES) +
                ' อยู่ ' + rng.choice(VALUES + PLACES))
    if r < 0.66:
        return (mangle('is') + ' ' + rng.choice(PLACES) + ' ' +
                mangle('in') + ' ' + rng.choice(PLACES + MISSES[:4]))
    if r < 0.76:
        return (mangle('is') + ' ' + rng.choice(KINDS) + ' ' +
                rng.choice(['a', 'an']) + ' ' +
                rng.choice(KINDS + MISSES[:4]))
    if r < 0.82:
        return mangle('where is') + ' ' + rng.choice(PLACES + KEYS[:4])
    if r < 0.89:
        return (mangle('what does') + ' ' +
                rng.choice(KEYS + PHRASES + ['mean', 'is-in', 'is-a', 'has',
                                             'ghost']) + ' ' +
                mangle('mean'))
    if r < 0.95:
        return (rng.choice(PHRASES + ['hello world', 'paris']) +
                rng.choice([' means ', ' หมายความว่า ', ' คือ ']) +
                rng.choice(VALUES + MISSES[:4]))
    return (rng.choice(KEYS + PLACES[:4]) +
            rng.choice([' อยู่ไหน', ' หมายความว่าอะไร']))


# Usage-cluster pools for the A10 lines: teaches share words so the
# co-occurrence counts build up, then queries hit the usage fallback
# and the usage-ranked clarification.
PETS = ['milo', 'somchai', 'felix', 'luna']
FOODS = ['fish', 'tuna', 'milk', 'rice', 'ปลา', 'ข้าว']


def a10_line():
    r = rng.random()
    if r < 0.35:
        return (mangle('remember') + ' ' + rng.choice(PETS) + ' ' +
                mangle('is fond of') + ' ' + rng.choice(FOODS))
    if r < 0.55:
        return (mangle('remember') + ' ' + rng.choice(PETS) + ' ' +
                mangle('is also') + ' ' +
                rng.choice(['a good hunter', 'allergic to ' + rng.choice(FOODS),
                            'fond of ' + rng.choice(FOODS)]))
    if r < 0.75:
        # A word that lives in taught values but is rarely a key.
        return mangle('what is') + ' ' + rng.choice(FOODS + ['fond'])
    if r < 0.90:
        return mangle('what is') + ' ' + rng.choice(PETS + MISSES[:4])
    return mangle('forget') + ' ' + rng.choice(PETS)


# Phrases for user-taught paraphrases, and miss-askings that overlap real
# keys by a word (to trigger the clarification dialogue).
PHRASES = ['the capital of france', 'kitty', 'สวัสดี', 'big answer']
MISSES = ['cat', 'answer', 'my', 'capital', 'ghost town', 'nothing',
          'คนไทย', 'ประเทศ', 'c', 'แมว', 'แมวc', 'car', 'red']


def mangle(word):
    # Random ASCII case + whitespace mangling; meaning must not change.
    s = ''.join(c.upper() if rng.random() < 0.4 else c for c in word)
    if rng.random() < 0.3:
        s = ' ' * rng.randrange(1, 3) + s
    if rng.random() < 0.3:
        s = s + rng.choice([' ', '  ', '\t']) * rng.randrange(1, 2)
    return s


def punctuate(line):
    if rng.random() < 0.25:
        return line + rng.choice(['?', '.'])
    return line


# Coherent A10 scenarios: clustered teaches build co-occurrence counts,
# then queries exercise the usage fallback (a word that lives in values
# but was never a key), the ranked clarification (usage beats insertion
# order), counting after correction and forget, and Thai tokens as
# whole words (no segmenter).
A10_SCENARIOS = [
    ['remember milo is fond of fish', 'remember luna is fond of fish',
     'remember felix is fond of tuna', 'what is fish', 'what is bread'],
    ['remember my cat is somchai', 'remember fat cat is lazy',
     'remember the fat cat is sleepy',
     'remember the fat cat is also very round',
     'what is cat', 'fat cat'],
    ['remember แมวดำ is ชอบ ปลา', 'remember หมาดำ is ชอบ กระดูก',
     'what is ปลา'],
    ['remember bob is fond of tea', 'remember bob is also fond of cake',
     'what is tea', 'forget bob', 'what is tea'],
]


# Coherent A9 scenarios spliced into sessions: random lines alone rarely
# line up a teach with its chain query, so these guarantee positive
# inference coverage (chains, where-is, built-in self-knowledge, Thai).
A12_SCENARIOS = [
    ['remember apple is a fruit', 'remember fruit is food',
     'is apple food', 'is apple a drink', 'is apple a food'],
    ['remember แมว เป็น สัตว์', 'remember สัตว์ เป็น สิ่งมีชีวิต',
     'แมวเป็นสิ่งมีชีวิตไหม', 'แมวเป็นปลาไหม',
     'แมว คือ สัตว์ หรือไม่', 'แมว คือ สัตว์?'],
    ['remember apple is a fruit', 'forget apple', 'what did you forget',
     'what have you forgotten'],
    ['remember apple is a fruit', 'what do you know',
     'how many things do you know', 'what did we talk about',
     'what happened this session'],
    ['kitty means my cat', 'kitty means my cat?',
     'ลิง คือ สัตว์', 'ลิง คือ สัตว์ ไหม'],
]


def a12_line():
    r = rng.random()
    if r < 0.25:
        return mangle(rng.choice(
            ['what do you know', 'how many things do you know',
             'what have you learned', 'what did you forget',
             'what have you forgotten', 'what did we talk about',
             'what happened this session']))
    if r < 0.45:
        return (mangle('is') + ' ' + rng.choice(KINDS) + ' ' +
                rng.choice(KINDS + MISSES[:4]))
    if r < 0.60:
        return (mangle('remember') + ' ' + rng.choice(KINDS) + ' ' +
                mangle('is') + ' ' + rng.choice(KINDS + VALUES))
    if r < 0.75:
        return (mangle('remember') + ' ' +
                rng.choice(['แมว', 'ลิง', 'หมา']) + ' เป็น ' +
                rng.choice(['สัตว์', 'สิ่งมีชีวิต', 'ปลา']))
    if r < 0.90:
        return (rng.choice(['แมว', 'ลิง', 'หมา']) + 'เป็น' +
                rng.choice(['สัตว์', 'สิ่งมีชีวิต', 'ปลา', 'ผลไม้']) +
                rng.choice(['ไหม', ' ไหม', 'หรือไม่', ' หรือไม่']))
    return (rng.choice(PHRASES + KINDS[:3]) +
            rng.choice([' means ', ' คือ ']) +
            rng.choice(KEYS + VALUES[:3]) + '?')


# Verb-relation pools for the A13 lines.
CRITTERS = ['a dog', 'a cat', 'a fish', 'a bird', 'a bat']
PROPS = ['energy', 'food', 'water', 'sleep']
ACTS = ['learn', 'fly', 'swim', 'run']


# Coherent A13 scenarios: verb relations inherited over is-a chains,
# active/passive equivalence, additive kinds, explicit negatives,
# contradictions, and the Thai negative kind.
A13_SCENARIOS = [
    ['remember a dog is a mammal', 'remember a mammal is an animal',
     'remember an animal is a living thing',
     'remember a living thing needs energy',
     'does dog need energy', 'is energy needed by a dog',
     'does dog need sleep'],
    ['remember a human is a mammal', 'remember a human can learn',
     'remember a doctor is a human', 'remember a doctor is a professional',
     'can a doctor learn', 'what is a doctor', 'is doctor a mammal'],
    ['remember a fish cannot fly', 'can a fish fly', 'can a fish swim',
     'remember a dog does not need sleep', 'does dog need sleep',
     'does dog need food'],
    ['remember a bat is a mammal', 'remember a bat is not a mammal',
     'is bat a mammal', 'remember a car uses fuel',
     'remember a car does not use fuel', 'does car use fuel'],
    ['remember แมว ไม่เป็น สัตว์', 'แมวเป็นสัตว์ไหม', 'แมวเป็นปลาไหม'],
]


# Coherent A14 scenarios: compositional rule chains, nested rules,
# the can-stays-can axiom, rule-vs-taught-negative contradictions,
# cycle termination. Deterministic fresh sessions, same reason as A13.
A14_SCENARIOS = [
    # R1 has+uses and its passive form; unknown subject stays unknown.
    # (A14.1: car/engine are taught as machines so the guards pass.)
    ['remember a car is a machine', 'remember a car has an engine',
     'remember an engine uses energy',
     'does a car use energy', 'is energy used by a car',
     'does a truck use energy'],
    # R3 then R2: two composed rule steps; capability evidence never
    # answers a doing question (can-stays-can axiom).
    ['remember a car is a machine', 'remember an engine is a machine',
     'remember a car has an engine', 'remember an engine uses energy',
     'remember energy can produce motion', 'can a car produce motion',
     'does a car produce motion'],
    # Nested rule derivation (R5 feeding R4); has stays non-transitive.
    ['remember a car is a machine', 'remember an engine is a machine',
     'remember a car has an engine', 'remember an engine uses steam',
     'remember steam produces motion', 'does a car produce motion',
     'is motion produced by a car', 'does a car have steam'],
    # Rule-derived positive vs taught negative: a contradiction that is
    # shown with its reasoning, never silently resolved.
    ['remember a car is a machine', 'remember a car does not use gasoline',
     'remember a car has an engine',
     'remember an engine uses gasoline', 'does a car use gasoline'],
    # A has-cycle terminates; a taught negative still beats inherited
    # positive evidence with no rule involvement.
    ['remember a motor is a machine',
     'remember a motor has a rotor', 'remember a rotor has a motor',
     'remember a rotor can spin', 'can a motor spin', 'can a motor fly',
     'remember a bird can fly', 'remember a penguin is a bird',
     'remember a penguin cannot fly', 'can a penguin fly'],
]

# Coherent A14.1 scenarios: domain guards in strict and explore modes,
# the three distinct blocked explanations, subclass membership through
# the is-a chain, assumption propagation across long chains, Thai
# negative domain teaches. Deterministic fresh sessions, as A13/A14.
A141_SCENARIOS = [
    # Strict mode blocks an unverified domain with its own explanation;
    # a premise-less question stays a plain unknown (no guard noise).
    ['remember a car has an engine', 'remember an engine uses energy',
     'does a car use energy', 'can a car fly'],
    # Negative domain evidence blocks in BOTH modes, same explanation.
    ['remember a pilot has a license', 'remember a license can expire',
     'remember a pilot is not a machine', 'can a pilot expire',
     'mode explore', 'can a pilot expire', 'mode strict'],
    # Conflicting domain evidence blocks and is reported, never
    # resolved arbitrarily - in both modes.
    ['remember a robot is a machine', 'remember a robot is not a machine',
     'remember a robot has a motor', 'remember a motor can spin',
     'can a robot spin', 'mode explore', 'can a robot spin', 'mode strict'],
    # Subclass membership satisfies the domain through the chain, and
    # the chain shows as the step's domain condition.
    ['remember a car is a vehicle', 'remember a vehicle is a machine',
     'remember a car has an engine', 'remember an engine uses energy',
     'does a car use energy'],
    # Explore mode: a multi-step derivation carries consolidated
    # assumptions, each linked to its step; strict blocks the same
    # world. Assumptions never become facts.
    ['mode explore', 'remember a car has an engine',
     'remember an engine uses energy', 'remember energy can produce motion',
     'can a car produce motion', 'mode strict', 'can a car produce motion'],
    # A14.2 verification: a 5-step chain; the verified middle (m3)
    # drops out of the assumption list and shows its domain condition
    # instead; strict blocks the whole chain.
    ['mode explore', 'remember a m1 has a m2', 'remember a m2 has a m3',
     'remember a m3 has a m4', 'remember a m4 has a m5',
     'remember a m5 uses a m6', 'remember a m6 can move',
     'remember a m3 is a machine', 'can a m1 move',
     'mode strict', 'can a m1 move'],
    # Conditional conclusions stay conditional downstream: the carrier
    # builds on a conditional edge and every assumption propagates to
    # the final answer.
    ['mode explore', 'remember a car has an engine',
     'remember an engine uses energy', 'remember energy can produce motion',
     'remember a carrier has a car', 'can a carrier produce motion'],
    # A Thai negative domain teach participates in guards.
    ['remember a pilot has a license', 'remember a license can expire',
     'remember a pilot ไม่เป็น machine', 'can a pilot expire'],
]


def a13_line():
    r = rng.random()
    if r < 0.22:
        return (mangle('remember') + ' ' + rng.choice(CRITTERS) + ' ' +
                rng.choice(['needs', 'uses', 'produces', 'causes']) + ' ' +
                rng.choice(PROPS))
    if r < 0.40:
        return (mangle('remember') + ' ' + rng.choice(CRITTERS) + ' ' +
                mangle('can') + ' ' + rng.choice(ACTS))
    if r < 0.52:
        return (mangle('remember') + ' ' + rng.choice(CRITTERS) + ' ' +
                rng.choice(['cannot', 'can not', 'does not need',
                            'do not need']) + ' ' + rng.choice(ACTS + PROPS))
    if r < 0.66:
        return (mangle('does') + ' ' + rng.choice(CRITTERS + ['dog', 'cat']) +
                ' ' + rng.choice(['need', 'needs', 'use', 'uses',
                                  'produce', 'produces', 'cause', 'causes',
                                  'have', 'has']) + ' ' +
                rng.choice(PROPS + MISSES[:4]))
    if r < 0.78:
        return (mangle('can') + ' ' + rng.choice(CRITTERS + ['dog']) + ' ' +
                rng.choice(ACTS + MISSES[:4]))
    if r < 0.88:
        return (mangle('is') + ' ' + rng.choice(PROPS + ACTS) + ' ' +
                rng.choice(['needed by', 'used by', 'produced by',
                            'caused by']) + ' ' +
                rng.choice(CRITTERS + MISSES[:4]))
    if r < 0.95:
        return (mangle('remember') + ' ' + rng.choice(CRITTERS) + ' ' +
                mangle('is not') + ' ' + rng.choice(['a', 'an']) + ' ' +
                rng.choice(KINDS))
    return (mangle('remember') + ' ' + rng.choice(['แมว', 'ลิง', 'หมา']) +
            ' ไม่เป็น ' + rng.choice(['สัตว์', 'ปลา', 'นก']))


A9_SCENARIOS = [
    ['remember paris is in france', 'remember france is in europe',
     'is paris in europe', 'is paris in asia', 'where is paris',
     'where is ghost'],
    ['kitty means my cat', 'what does kitty mean',
     'what does mean mean', 'what does is-in mean',
     'what does is-a mean', 'what does has mean', 'what does ghost mean'],
    ['remember cat is a animal', 'remember animal is a living thing',
     'is cat a living thing', 'is cat a fish', 'remember cat has whiskers'],
    ['remember แมว อยู่ สวน', 'แมว อยู่ไหน',
     'remember ลิง คือ สัตว์', 'ลิง หมายความว่าอะไร',
     'ลิง คือ ตัวอะไร'],
    ['remember วัด มี พระ', 'what do you know about วัด',
     'remember วัด มี เจดีย์', 'remember วัด อยู่ เมือง',
     'remember ก อยู่ ข มี ค', 'what do you know about ก', 'remember แมว มี',
     'remember มี พระ', 'remember a temple is a building',
     'remember a building มี ผนัง', 'does a temple have ผนัง',
     'what do you know about a building', 'forget วัด',
     'what do you know about วัด', 'what do you know'],
    ['remember นกฮูก อยู่ ป่า', 'remember นกฮูก คือ นก', 'remember นกฮูก มี ปีก',
     'no, นกฮูก อยู่ สวน', 'what do you know about นกฮูก', 'นกฮูก อยู่ไหน',
     'no, ผี อยู่ วัด', 'no, นกฮูก เป็น สัตว์', 'no, นกฮูก คือ นกกลางคืน',
     'no, นกฮูก มี ตา', 'what do you know about นกฮูก',
     'ฮูก means นกฮูก', 'no, ฮูก อยู่ ถ้ำ', 'นกฮูก อยู่ไหน',
     'remember ค อยู่ ก', 'remember ค is also อยู่ ข', 'no, ค อยู่ ง',
     'what do you know about ค', 'no, นกฮูก is a bird',
     'what do you know about นกฮูก', 'no, อยู่ ที่นี่', 'no, ก อยู่'],
    ['มัน อยู่ไหน', 'remember ค้างคาว อยู่ ถ้ำ', 'มัน อยู่ไหน', 'อันนั้น คืออะไร',
     'เกี่ยวกับ เขา', 'มัน คือ สัตว์ หรือไม่', 'มันเป็นสัตว์ไหม', 'ตัว นั้น อยู่ไหน',
     'remember มัน อยู่ ที่นี่', 'มัน อยู่ไหน', 'remember มันฝรั่ง อยู่ ดิน',
     'มันฝรั่ง อยู่ไหน', 'ช้าง อยู่ไหน', 'ที่ นั่น มี อะไร บ้าง', 'forget มัน',
     'มัน อยู่ไหน', 'what do you know'],
]


def make_session():
    oracle = Oracle()
    lines = []
    replies = []
    for _ in range(45):
        r = rng.random()
        if r < 0.19:
            key = rng.choice(KEYS)
            value = rng.choice(VALUES)
            line = mangle('remember') + ' ' + mangle(key) + ' ' + \
                mangle('is') + ' ' + value
        elif r < 0.25:
            key = rng.choice(KEYS)
            value = rng.choice(VALUES)
            line = mangle('remember') + ' ' + mangle(key) + ' ' + \
                mangle('is also') + ' ' + value
        elif r < 0.35:
            line = mangle('what is') + ' ' + mangle(rng.choice(KEYS))
        elif r < 0.43:
            line = mangle(rng.choice(ALIASES)) + ' ' + mangle(rng.choice(KEYS))
        elif r < 0.47:
            line = mangle('what is') + ' ' + mangle(rng.choice(PHRASES))
        elif r < 0.53:
            line = mangle('what do you know about') + ' ' + mangle(rng.choice(KEYS))
        elif r < 0.57:
            line = mangle('what about it')
        elif r < 0.62:
            line = mangle(rng.choice(PHRASES)) + ' ' + mangle('means') + \
                ' ' + mangle(rng.choice(KEYS))
        elif r < 0.66:
            line = mangle(rng.choice(['what is', 'do you know'])) + ' ' + \
                mangle(rng.choice(MISSES))
        elif r < 0.71:
            line = 'no, ' + rng.choice(KEYS + PHRASES) + ' ' + \
                mangle('is') + ' ' + rng.choice(VALUES)
        elif r < 0.74:
            line = rng.choice(['yes', 'no', 'Yes', 'No', 'YES'])
        elif r < 0.77:
            line = mangle('forget') + ' ' + mangle(rng.choice(KEYS + ['ghost']))
        elif r < 0.81:
            line = mangle('forget it')
        elif r < 0.86:
            line = mangle('note') + ' ' + rng.choice(VALUES + ['Mixed CASE note'])
        elif r < 0.89:
            line = mangle('notes')
        elif r < 0.91:
            line = mangle('clear notes')
        elif r < 0.93:
            line = mangle('list')
        elif r < 0.94:
            line = mangle('say') + ' ' + rng.choice(VALUES + ['Mixed CASE text'])
        elif r < 0.945:
            line = mangle('help')
        elif r < 0.965:
            line = a8_line()
        elif r < 0.978:
            line = a9_line()
        elif r < 0.988:
            line = a10_line()
        elif r < 0.993:
            line = a12_line()
        elif r < 0.998:
            line = a13_line()
        else:
            line = rng.choice(GARBAGE)
        line = punctuate(line)
        lines.append(line)
    if rng.random() < 0.7:
        pos = rng.randrange(len(lines) + 1)
        lines[pos:pos] = list(rng.choice(A9_SCENARIOS + A10_SCENARIOS +
                                         A12_SCENARIOS + A13_SCENARIOS))
    replies = [oracle.respond(line) for line in lines]
    return lines, replies, oracle


sessions = [make_session() for _ in range(25)]
# A13 scenarios are semantic, not probabilistic: run each in its own
# fresh session so every inheritance/negative/contradiction path is
# covered on every run.
# Coherent A15 scenarios: bounded hypothesis learning over A14.1
# explore-mode assumptions. Candidates are unresolved knowledge gaps,
# never facts; strict mode records nothing; teaching or explicit
# forgets are the only way out.
A15_SCENARIOS = [
    # Recording, dedup within one derivation, listing, detail
    # provenance, isolation (strict blocks and queries stay unknown).
    ['mode explore', 'remember a car has an engine',
     'remember an engine uses energy', 'remember energy can produce motion',
     'can a car produce motion', 'can a car fly', 'hypotheses',
     'hypotheses detail', 'mode strict', 'can a car produce motion',
     'is a car a machine', 'hypotheses'],
    # Teaching retires deterministically: a positive teach lets strict
    # pass; the retired entry is shown.
    ['mode explore', 'remember a bike has a dynamo',
     'remember a dynamo can produce electricity',
     'can a bike produce electricity', 'hypotheses',
     'remember a bike is a machine', 'hypotheses',
     'mode strict', 'can a bike produce electricity'],
    # A negative teach retires and leaves strict blocked; a candidate
    # is not positive evidence, so there is no conflict.
    ['mode explore', 'remember a pilot has a license',
     'remember a license can expire', 'can a pilot expire', 'hypotheses',
     'remember a pilot is not a machine', 'hypotheses',
     'can a pilot expire'],
    # Explicit forget frees space (and reports a miss for unknown
    # entries); clear empties both lists.
    ['mode explore', 'remember a boat has a sail',
     'remember a sail can catch wind', 'can a boat catch wind',
     'forget hypothesis a boat is a machine', 'hypotheses',
     'forget hypothesis a boat is a machine', 'clear hypotheses',
     'hypotheses'],
    # Thai subjects are candidates too.
    ['mode explore', 'remember a หุ่นยนต์ has a motor',
     'remember a motor can spin', 'can a หุ่นยนต์ spin', 'hypotheses'],
    # Provenance bounding: 12 derivations on one candidate keep the
    # creation event plus 10 detailed later uses; 1 marked omitted.
    (['mode explore', 'remember a rig has a crane',
      'remember a crane can lift'] + ['can a rig lift'] * 12 +
     ['hypotheses detail']),
]

A16_SCENARIOS = [
    # 1. Basic extraction, listing, detail provenance.
    ['read a car is a machine. a car has an engine. a car needs fuel',
     'readings', 'readings detail'],
    # 2. Modal/hedged segments skip; the plain one extracts.
    ['read the sky might be green. a frog may be a prince. water is wet. it could rain',
     'readings'],
    # 3. Negation polarity preserved on the record.
    ['read a bat is not a bird', 'readings'],
    # 4. Two sources, opposite polarity: CONFLICT, independence noted.
    ['read manual: a bat is a bird.',
     'read wiki: a bat is not a bird.', 'readings'],
    # 5. Same source repeating a claim counts once.
    ['read dup: a car is a machine.',
     'read dup: a car is a machine.', 'readings about a car'],
    # 6. MULTI_SOURCE readings never enter strict or explore
    # inference; the queries behave as if the read never happened.
    ['read s1: a zorg is a machine.', 'read s2: a zorg is a machine.',
     'is a zorg a machine', 'mode explore', 'is a zorg a machine',
     'can a zorg fly', 'what is a zorg', 'hypotheses', 'mode strict',
     'readings about a zorg'],
    # 7. Teaching marks USER_CONFIRMED on the matching polarity and
    # USER_DISPUTED on recorded opposite support (v0.11.1:
    # polarity-scoped, evidence conflict retained). Provenance kept.
    ['read a car is a machine.', 'remember a car is a machine',
     'readings about a car',
     'read wiki: a bat is not a bird.', 'remember a bat is a bird',
     'readings about a bat', 'readings detail'],
    # 8. Embedded commands in a payload are data, never executed:
    # mode stays strict, readings survive.
    ['read mode explore. clear readings. a cat is a pet',
     'mode', 'readings'],
    # 9. Cap 100: new distinct candidates refused and reported, no
    # eviction; updates to existing records still accepted.
    (['read ' + ' '.join('a item%03d is a machine.' % i
                        for i in range(1, 102))] +
     ['read second: a item001 is a machine.',
      'read second: a item999 is a machine.',
      'readings about a item001']),
    # 10. Same source contradicting itself: SOURCE-INTERNAL CONFLICT,
    # both readings persist.
    ['read dup: a car is a machine. a car is not a machine.',
     'readings about a car'],
    # Thai extraction on the existing teach shapes, with honest
    # segment/match counts - never "sentences understood".
    ['read รถยนต์ เป็น ยานพาหนะ. แมว อยู่ บ้าน. นก ไม่เป็น สัตว์เลี้ยง',
     'readings', 'readings detail'],
    # Isolation regression: after reads, strict/explore queries,
    # guards, recall, did-you-mean and hypothesis generation behave
    # exactly as in the no-read session below (same battery).
    ['read s1: a glorp is a machine. a glorp can fly.',
     'is a glorp a machine', 'mode explore', 'can a glorp fly',
     'is a glorp needed by a car', 'mode strict', 'what is a glorp',
     'do you know glorp', 'what do you know', 'hypotheses'],
    ['is a glorp a machine', 'mode explore', 'can a glorp fly',
     'is a glorp needed by a car', 'mode strict', 'what is a glorp',
     'do you know glorp', 'what do you know', 'hypotheses'],
    # v0.11.1 polarity-scoped alignment, four combos: single-side
    # confirm, single-side dispute, dual-side teach-positive and
    # teach-negative (evidence CONFLICT retained in both).
    ['read a car is a machine.', 'remember a car is a machine',
     'readings about a car'],
    ['read wiki: a bat is not a bird.', 'remember a bat is a bird',
     'readings about a bat'],
    ['read manual: a bat is a bird.', 'read wiki: a bat is not a bird.',
     'remember a bat is a bird', 'readings about a bat'],
    ['read manual: a bat is a bird.', 'read wiki: a bat is not a bird.',
     'remember a bat is not a bird', 'readings about a bat',
     'readings detail'],
    # Repeated teaching: labels are assignments, evidence lists never
    # gain duplicate entries; a contradictory later assertion goes
    # through the asserted-store conflict mechanism.
    ['read a car is a machine.', 'remember a car is a machine',
     'remember a car is a machine', 'readings detail',
     'remember a car is not a machine', 'readings about a car',
     'is a car a machine'],
    # Isolation with alignment set: confirmed/disputed readings still
    # never enter strict/explore inference (zorg is untaught).
    ['read s1: a zorg is a machine.', 'read s2: a zorg is not a machine.',
     'remember a zorg has a wing', 'is a zorg a machine',
     'mode explore', 'can a zorg fly', 'hypotheses', 'mode strict',
     'readings about a zorg'],
    # Management: forget reading, clear readings, empty listings,
    # auto vs named sources.
    ['readings', 'readings about a car',
     'read a car is a machine. a bat is a bird',
     'forget reading a car is a machine',
     'forget reading a car is a machine',
     'forget reading nonsense',
     'clear readings', 'readings', 'readings detail'],
]

A17_SCENARIOS = [
    # 1. Skip-class precedence: attribution counts as quoted even
    # with a modal present; modal beats the multi-clause class.
    ['read the guide says a kiwi might be a bird. a bat is a bird',
     'read a car, it seems, might fly. a frog is an animal',
     'readings'],
    # 2. The modal-hedged class never swallows supported can forms.
    ['read a car can fly. a plane cannot swim', 'readings'],
    # 3. Conjunction: first ' and ' split, both sides extract, spans
    # are the side texts.
    ['read a car is a machine and a bike is a vehicle', 'readings',
     'readings detail'],
    # 4. Conjunction is strictly atomic: one failing side skips the
    # whole segment as multi-clause.
    ['read a car is red and fast. a car is a machine and it is fast',
     'readings'],
    # 5. Plural patterns, distinct ids and polarity.
    ['read robots are machines. cats are not dogs. birds have wings. snakes do not have legs',
     'readings'],
    # 6. Plural teach forms confirm plural readings; the is-in fix
    # lets a taught is-in edge confirm a read one.
    ['read wiki: robots are machines. paris is in france',
     'remember robots are machines',
     'remember paris is in france', 'readings'],
    # 7. Pronoun and existential subjects are unmatched, never
    # guessed.
    ['read there are seven continents on earth. you are what you eat',
     'readings'],
]

A18_SCENARIOS = [
    # URL policy: every rejection happens before any network access,
    # so these replies are deterministic on every route. Valid URLs
    # fetch, so they live in the semantic fetch tests, never here.
    ['read url https://example.com/page',
     'read url http://user:secret@example.com/x',
     'read url http://example.com:8080/x',
     'read url http://example.com:99999/x',
     'read url http://127.0.0.1/admin',
     'read url http://192.168.1.1/',
     'read url http://EXAMPLE.com/A?B=c#frag',
     'read url http://example.com:80/x'],
]

A19_SCENARIOS = [
    # 1. Directive skip class: agent commands and web imperatives
    # inside a payload are skipped whole and stay inert (the state
    # is NOT cleared, the mode does NOT change); ordinary
    # declaratives containing the same words elsewhere extract or
    # stay unmatched as before. Readings never answer questions.
    ['read remember a car is a machine. mode explore. clear readings. quit. click here. subscribe now. download this file. a frog is an animal',
     'readings', 'mode', 'is a frog an animal'],
    # 2. Skip precedence: quoted/attribution beats directive even
    # when the directive word leads the quoted text; directive beats
    # modal on the same segment.
    ['read the guide says remember a car is a machine. remember a car might fly. a bat is a bird',
     'readings'],
    # 3. No general imperative parser: a declarative that merely
    # contains a command word away from the start is not a
    # directive (unmatched, not skipped).
    ['read i remember my first car. the download button is red. a sparrow is a bird',
     'readings'],
    # 4. Thai-Latin boundary: both sides validate -> two extractions
    # with the side texts as spans; either side ambiguous -> the
    # whole segment is skipped as thai-boundary-ambiguous.
    ['read นก เป็น สัตว์ a hornbill is a bird',
     'read นกมีปีกและบินได้ a hornbill is a bird',
     'readings detail'],
    # 5. แล้ว/ครับ are never terminators: แล้ว stays inside the
    # extracted object when the Thai side still validates.
    ['read วาฬ เป็น สัตว์ แล้ว a frog is an animal', 'readings'],
    # 6. Pure Thai regressions: no transition, extraction unchanged.
    ['read วาฬ เป็น สัตว์เลี้ยงลูกด้วยนม. ค้างคาว ไม่เป็น นก',
     'readings'],
    # 7. Measurements: typed sources on the same claim; typed
    # sources never count as domains, and content clusters are
    # reported NOT_ASSESSED (A20: similarity is not copying proof).
    ['read a1: birds have wings', 'read a2: birds has wings',
     'read a3: birds have wings', 'readings'],
    # 8. A later conflicting reading raises an evidence-review
    # warning (CONFLICT across sources; SCOPE_MISMATCH inside one
    # source) and never alters accepted knowledge: the taught fact
    # still answers, and a conflicting reading on a USER_CONFIRMED
    # claim only marks it for review.
    ['remember a penguin is a bird',
     'read m1: a penguin is not a bird',
     'is a penguin a bird',
     'read m1: a penguin is a bird. a penguin is not a bird',
     'readings about a penguin'],
    # 9. SOURCE_DIVERSITY_THRESHOLD_MET (renamed REVIEW_ELIGIBLE)
    # is reachable only when every threshold holds: 3 typed sources
    # but no registrable domains, so NOT eligible; the claim stays
    # MULTI_SOURCE with independence UNVERIFIED.
    ['read b1: a kiwi is a bird', 'read b2: a kiwi is a bird',
     'read b3: a kiwi is a bird', 'readings about a kiwi'],
    # 10. Approval/revocation history: teaching confirms, and a
    # later forget revokes the alignment - recorded, never silent.
    ['read m1: a frog is an animal', 'remember a frog is an animal',
     'readings detail', 'forget a frog', 'readings detail'],
]

A19LIN_SCENARIOS = [
    # A19 lineage labels: one corpus lineage is ONE source forever.
    # SINGLE_CORPUS marks corpus-only support distinctly; UNVERIFIED
    # still shows, and MULTI_SOURCE is never manufactured from one
    # corpus.
    ['read corpus simplewiki-corpus: a krill is a crustacean',
     'readings about a krill', 'readings detail'],
    # Reading the same lineage again (a refreshed dump) never forks
    # the source: the registry still holds exactly corpus-1.
    ['read corpus simplewiki-corpus: a krill is a crustacean',
     'read corpus simplewiki-corpus: a krill has an exoskeleton',
     'readings detail'],
    # Corpus + typed source: two independent groups, MULTI_SOURCE,
    # the corpus lineage counted separately from domains.
    ['read corpus simplewiki-corpus: a krill is a crustacean',
     'read fieldnotes: a krill is a crustacean', 'readings about a krill'],
    # Two corpus lineages: two groups, MULTI_SOURCE.
    ['read corpus simplewiki-corpus: a krill is a crustacean',
     'read corpus other-corpus: a krill is a crustacean',
     'readings about a krill'],
    # Corpus + two typed sources: 3 sources but no registrable
    # domains, so never SOURCE_DIVERSITY_THRESHOLD_MET.
    ['read corpus simplewiki-corpus: a krill is a crustacean',
     'read n1: a krill is a crustacean',
     'read n2: a krill is a crustacean', 'readings about a krill'],
    # Malformed forms: clear errors, nothing registered.
    ['read corpus simplewiki-corpus a krill is a crustacean',
     'read corpus BAD: a krill is a crustacean', 'readings detail'],
    # clear readings resets the corpus registry too.
    ['read corpus simplewiki-corpus: a krill is a crustacean',
     'clear readings',
     'read corpus simplewiki-corpus: a krill is a crustacean',
     'readings detail'],
]

# R1a: Thai reply twins. Pure-Thai lines only; English-framed Thai
# commands keep English acks by design. Covers: means-ack, Thai recall
# glue with ' คือ ' strip and ' และ ' join, where/mean fallbacks,
# unknown-usage fallback, did-you-mean pending question, final fallback.
R1A_SCENARIOS = [
    ['ม้า คือ สัตว์', 'ม้า คืออะไร', 'ม้า คือ ผี', 'ม้า คืออะไร',
     'ม้า หมายความว่าอะไร'],
    ['remember นกฮูก คือ นก', 'นกฮูก คืออะไร', 'นกฮูก อยู่ไหน'],
    ['remember ม้า คือ สัตว์', 'remember ม้า เป็น สัตว์', 'ม้า คืออะไร'],
    ['remember ม้า คือ สัตว์', 'remember ม้า คือ ผี', 'ม้า คืออะไร'],
    ['ผี คืออะไร', 'ผี อยู่ไหน', 'ผี หมายความว่าอะไร'],
    ['remember แมว คือ สัตว์', 'remember มด คือ สัตว์',
     'แมวมด คืออะไร', 'yes', 'แมว คืออะไร'],
    ['ขขขข', 'ม้า เป็น สัตว์ ไหม', 'ม้า คือ สัตว์ หรือไม่'],
]
for _sc in (A13_SCENARIOS + A14_SCENARIOS + A141_SCENARIOS +
            A15_SCENARIOS + A16_SCENARIOS + A17_SCENARIOS +
            A18_SCENARIOS + A19_SCENARIOS + A19LIN_SCENARIOS +
            R1A_SCENARIOS):
    _o = Oracle()
    _lines = list(_sc)
    sessions.append((_lines, [_o.respond(l) for l in _lines], _o))


LD = [['pc-aa01', 'owns', 'has', 'pos'], ['pc-bb02', 'owns', 'means', 'pos'],
      ['pc-cc03', 'is', 'means', 'pos'],
      ['pc-dd04', 'sits on', 'is-in', 'pos']]
LEARNED_CASES = [
    [LD, ['read s1: a crow owns a nest', 'read s1: a crow owns a nest',
          'read s2: A  Crow   OWNS a nest. a hawk owns a nest',
          'readings', 'facts']],
    # handwritten reader wins: "is a" is the reader's own pattern, so a
    # learned "is" never fires there; skip classes also win.
    [LD, ['read s1: a kiwi is a bird. "a crow owns a nest". '
          'the guide says a gull owns a nest',
          'read s2: a robin might own a nest. remember a wren owns a nest',
          'readings detail']],
    # structure rules: stopword slot, 5-token slot, verb twice, bare verb,
    # non-ASCII, multi-clause conjunction, quoted.
    [LD, ['read s1: it owns a nest. one two three four five owns a nest',
          'read s2: a crow owns owns a nest. owns a nest. a crow owns',
          'read s3: a cr\u00f3w owns a nest. a crow owns a nest and '
          'a hawk owns a nest',
          'read s4: a gull sits on a post. the cat sits on a mat']],
    [[], ['read s1: a crow owns a nest', 'readings']],
    [LD[:1], ['read s1: a crow owns a nest', 'read s2: a crow owns a nest',
              'read s3: a hawk owns a nest', 'forget a crow', 'readings']],
]
for _lc in LEARNED_CASES:
    _o = Oracle()
    _o.learned = _lc[0]
    _lc.append([_o.respond(l) for l in _lc[1]])
    _lc.append(_o)

expected_lines = []
for lines, replies, oracle in sessions:
    expected_lines.extend(replies)
    expected_lines.append('keys ' + str(len(oracle.order)))
    for k in oracle.order:
        expected_lines.append(k + ' => ' + ' | '.join(oracle.facts[k]))
    expected_lines.append('aliases ' + str(len(oracle.aliases)))
    for a, t in oracle.aliases.items():
        expected_lines.append(a + ' ~> ' + t)
    expected_lines.append('rels ' + str(len(oracle.rels)))
    for edge in oracle.rels:
        expected_lines.append('rel ' + ' | '.join(edge))
    expected_lines.append('notes ' + str(len(oracle.notes)))
    for i, note in enumerate(oracle.notes):
        expected_lines.append('note ' + str(i + 1) + ' = ' + note)
    expected_lines.append('topic ' + (oracle.topic if oracle.topic is not None else 'none'))
for _d, _l, _r, _o in LEARNED_CASES:
    expected_lines.extend(_r)
    expected_lines.append('learned ' + str(len(_o.learned_readings)))
    for _e in _o.learned_readings:
        expected_lines.append('lr ' + ' | '.join(_e[:7]) + ' | ' +
                              ('true' if _e[7] else 'false'))
    expected_lines.append('readings ' + str(len(_o.readings)) +
                          ' facts ' + str(len(_o.facts)))
total = sum(len(replies) for _, replies, _ in sessions)
total += sum(len(_r) for _, _, _r, _ in LEARNED_CASES)
expected_lines.append('total ' + str(total))
expected = '\n'.join(expected_lines) + '\n'


def lit(value):
    # hs string escapes cover only \n \t \r \" \\ \0; the corpus avoids
    # every other control character and emits Unicode literally.
    return json.dumps(value, ensure_ascii=False)


text = 'import agent.core\n'
text += 'sessions = ' + lit([lines for lines, _, _ in sessions]) + '\n'
text += 'total = 0\n'
text += 'for session in sessions:\n'
text += '  state = agent.core.new_state()\n'
text += '  for line in session:\n'
text += '    print agent.core.respond(state, line)\n'
text += '    total = total + 1\n'
text += '  print "keys " + str(len(state["order"]))\n'
text += '  for k in state["order"]:\n'
text += '    joined = ""\n'
text += '    for v in state["facts"][k]:\n'
text += '      if joined == "":\n'
text += '        joined = v\n'
text += '      else:\n'
text += '        joined = joined + " | " + v\n'
text += '    print k + " => " + joined\n'
text += '  print "aliases " + str(len(state["aliases"]))\n'
text += '  for a in state["aliases"]:\n'
text += '    print a + " ~> " + state["aliases"][a]\n'
text += '  print "rels " + str(len(state["rels"]))\n'
text += '  for r in state["rels"]:\n'
text += '    print "rel " + r[0] + " | " + r[1] + " | " + r[2]\n'
text += '  print "notes " + str(len(state["notes"]))\n'
text += '  i = 0\n'
text += '  while i < len(state["notes"]):\n'
text += '    print "note " + str(i + 1) + " = " + state["notes"][i]\n'
text += '    i = i + 1\n'
text += '  if state["topic"] == null:\n'
text += '    print "topic none"\n'
text += '  else:\n'
text += '    print "topic " + state["topic"]\n'
text += 'learned_cases = ' + lit([[c[0], c[1]] for c in LEARNED_CASES]) + '\n'
text += 'for case in learned_cases:\n'
text += '  state = agent.core.new_state()\n'
text += '  state["learned"] = []\n'
text += '  for d in case[0]:\n'
text += '    append(state["learned"], d)\n'
text += '  for line in case[1]:\n'
text += '    print agent.core.respond(state, line)\n'
text += '    total = total + 1\n'
text += '  lrs = []\n'
text += '  if "learned_readings" in state:\n'
text += '    lrs = state["learned_readings"]\n'
text += '  print "learned " + str(len(lrs))\n'
text += '  for e in lrs:\n'
text += '    fl = "false"\n'
text += '    if e[7]:\n'
text += '      fl = "true"\n'
text += '    print "lr " + e[0] + " | " + e[1] + " | " + e[2] + " | " + e[3] + " | " + e[4] + " | " + e[5] + " | " + e[6] + " | " + fl\n'
text += '  print "readings " + str(len(state["readings"])) + " facts " + str(len(state["order"]))\n'
text += 'print "total " + str(total)\n'

STORE_PROG = '''import agent.core
import agent.store
p = {path}
s = agent.core.new_state()
print agent.core.respond(s, "remember alpha is one")
print agent.core.respond(s, "remember alpha is also two")
print agent.core.respond(s, "a1 means alpha")
print agent.core.respond(s, "note buy milk")
print agent.core.respond(s, "remember paris is in france")
print agent.core.respond(s, "remember france is in europe")
agent.store.save(s, p)
s2 = agent.store.load(p)
print agent.core.respond(s2, "what is alpha")
print agent.core.respond(s2, "what is a1")
print agent.core.respond(s2, "is paris in europe")
print agent.core.respond(s2, "is paris in asia")
print agent.core.respond(s2, "where is paris")
print agent.core.respond(s2, "list")
print agent.core.respond(s2, "notes")
print agent.core.respond(s2, "forget alpha")
print agent.core.respond(s2, "what is a1")
agent.store.save(s2, p)
s3 = agent.store.load(p)
print agent.core.respond(s3, "list")
print agent.core.respond(s3, "is paris in europe")
'''
STORE_WANT = ('remembered alpha is one (filed as a kind-of)\nadded: alpha is two (filed as a kind-of)\n'
              'ok, a1 means alpha\nnoted\n'
              'remembered paris is in france\n'
              'remembered france is in europe\n'
              'i know alpha is one and two\ni know alpha is one and two\n'
              'yes: paris is in france, france is in europe\n'
              'not that i know\nparis is in france, france is in europe\n'
              'i know 3 things: alpha, paris, france\nno notes yet\n'
              'forgot alpha\n'
              'i do not know a1\ni know 2 things: paris, france\n'
              'yes: paris is in france, france is in europe\n')

FRESH_PROG = '''import agent.core
import agent.store
s = agent.core.new_state()
print agent.core.respond(s, "list")
s2 = agent.store.load({path})
print agent.core.respond(s2, "list")
'''

# A file in the pre-v3 on-disk shape (string fact values, no aliases)
# must load: values migrate to one-fact lists, aliases default empty.
V02_PROG = '''import agent.core
import agent.store
s = agent.store.load({path})
print agent.core.respond(s, "what is a")
print agent.core.respond(s, "list")
print agent.core.respond(s, "notes")
agent.store.save(s, {path})
s2 = agent.store.load({path})
print agent.core.respond(s2, "what is a")
'''
V02_WANT = ('i know a is 1\ni know 1 thing: a\nno notes yet\n'
            'i know a is 1\n')

# A v3 on-disk file (list-shaped facts + aliases, no "rels" key) must
# load: relation edges are derived from the fact values' shapes.
V03_PROG = '''import agent.core
import agent.store
s = agent.store.load({path})
print agent.core.respond(s, "is paris in europe")
print agent.core.respond(s, "where is paris")
agent.store.save(s, {path})
'''
V03_WANT = ('yes: paris is in france, france is in europe\n'
            'paris is in france, france is in europe\n')


def run_ref(source_path, timeout=120):
    return subprocess.run([sys.executable, str(ROOT/'interp.py'), str(source_path)],
                          env=env, capture_output=True, text=True, timeout=timeout)


def check_store_routes():
    with tempfile.TemporaryDirectory(prefix='hs-agent-store-') as tmp:
        d = Path(tmp)
        store = d/'mem.json'
        prog = d/'store.holy'
        prog.write_text(STORE_PROG.format(path=lit(str(store))), encoding='utf-8')
        r = run_ref(prog)
        assert r.returncode == 0 and not r.stderr, (r.returncode, r.stderr[-1500:])
        assert r.stdout == STORE_WANT, (r.stdout, STORE_WANT)
        # Missing file and corrupt files load as a fresh empty state.
        for name, body in [('missing', None), ('garbage', 'not json{'),
                           ('wrongshape', '{"nope": 1}'), ('empty', '')]:
            p = d/name
            if body is not None:
                p.write_text(body, encoding='utf-8')
            fprog = d/('fresh-' + name + '.holy')
            fprog.write_text(FRESH_PROG.format(path=lit(str(p))), encoding='utf-8')
            r = run_ref(fprog)
            want = 'i know nothing yet\ni know nothing yet\n'
            assert r.returncode == 0 and r.stdout == want, (name, r.returncode,
                                                            r.stdout, r.stderr[-500:])
        # Pre-v3 on-disk format migrates and round-trips into v3.
        v02 = d/'v02.json'
        v02.write_text('{"facts": {"a": "1"}, "order": ["a"]}', encoding='utf-8')
        vprog = d/'v02.holy'
        vprog.write_text(V02_PROG.format(path=lit(str(v02))), encoding='utf-8')
        r = run_ref(vprog)
        assert r.returncode == 0 and r.stdout == V02_WANT, (r.returncode,
                                                            r.stdout, r.stderr[-500:])
        # A v3 file (no "rels") derives relation edges on load.
        v03 = d/'v03.json'
        v03.write_text('{"facts": {"paris": ["in france"], '
                       '"france": ["in europe"]}, '
                       '"order": ["paris", "france"], '
                       '"aliases": {}}', encoding='utf-8')
        v3prog = d/'v03.holy'
        v3prog.write_text(V03_PROG.format(path=lit(str(v03))), encoding='utf-8')
        r = run_ref(v3prog)
        assert r.returncode == 0 and r.stdout == V03_WANT, (r.returncode,
                                                            r.stdout, r.stderr[-500:])
        assert '"rels"' in v03.read_text(encoding='utf-8')
    print('ok agent.store roundtrip + 4 fresh-load cases + pre-v3/v3 migration (reference route)', flush=True)


def verify(label, r):
    assert r.returncode == 0, (label, r.returncode, r.stderr[-1500:])
    assert not r.stderr, (label, r.stderr[-1500:])
    assert r.stdout == expected, (label, r.stdout[-2000:], expected[-2000:])
    print('ok agent.core corpus', label, total, 'replies', flush=True)


with tempfile.TemporaryDirectory(prefix='hs-agent-') as tmp:
    d = Path(tmp)
    source = d/'chat.holy'
    source.write_text(text, encoding='utf-8')
    verify('reference', run_ref(source))
    # The reference IR executor is independent of native code generation.
    old = os.environ.get('HSPATH')
    os.environ['HSPATH'] = env['HSPATH']
    try:
        interp.reset_parse_state()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            ir.run_module(ir.build_module(interp.parse_program(text)), str(d))
        verify('reference-ir', subprocess.CompletedProcess([], 0, output.getvalue(), ''))
    finally:
        if old is None: os.environ.pop('HSPATH', None)
        else: os.environ['HSPATH'] = old
    runner = []
    if platform.machine() not in ('x86_64', 'amd64'):
        qemu = shutil.which('qemu-x86_64')
        if not qemu:
            print('skip hosted x86 path routes: qemu-x86_64 unavailable')
            raise SystemExit(0)
        runner = [qemu]
    old = os.environ.get('HSPATH')
    os.environ['HSPATH'] = env['HSPATH']
    try:
        for label, build in [('ir-x64', x64gen.build_x64), ('ast-x64', x64gen.build_x64_ast)]:
            image = d/label
            with contextlib.redirect_stdout(io.StringIO()):
                rc = build(str(source), str(image))
            assert rc == 0 and image.exists(), label
            verify(label, subprocess.run(runner + [str(image)], env=env,
                     capture_output=True, text=True, timeout=120))
    finally:
        if old is None: os.environ.pop('HSPATH', None)
        else: os.environ['HSPATH'] = old
    for label, src in [('seed-native', source), ('hs-interpreter', ROOT/'selfhost/be/irinterp_run.holy')]:
        image = d/label
        r = subprocess.run(runner + [str(ROOT/'bootstrap/hs-hosted-x86_64'), str(src), str(image)],
                           env=env, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0 and image.exists(), (label, r.stdout[-500:], r.stderr[-500:])
        command = runner + [str(image)]
        if label == 'hs-interpreter': command.append(str(source))
        verify(label, subprocess.run(command, env=env, capture_output=True, text=True, timeout=120))
    if '--skip-gcc' not in sys.argv:
        verify('gcc-native', subprocess.run([sys.executable, str(ROOT/'hs.py'), 'run', str(source), '--backend', 'native'],
                env=env, capture_output=True, text=True, timeout=180))
check_store_routes()
print(str(6 if '--skip-gcc' in sys.argv else 7) + '/7 agent.core execution routes; ' + str(total) + ' replies each')
