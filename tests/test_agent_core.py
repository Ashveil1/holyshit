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
        "<fact> | remember <thing> has <part> | no, <thing> is <fact> | "
        "what is <thing> | do you know <thing> | what does <thing> mean | "
        "is <thing> in <thing> | where is <thing> | "
        "what do you know about <thing> | "
        "how is <thing> | how about <thing> | <thing> คืออะไร | "
        "<thing> หมายความว่าอะไร | <thing> อยู่ไหน | "
        "and <thing> | what else | what about it | <phrase> means <thing> | "
        "forget <thing> | "
        "forget it | note <text> | notes | clear notes | list | "
        "say <text> | help")
WS = ' \t\n\r'
STOP = {'the', 'and', 'for', 'are', 'with', 'that', 'this'}


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
            return 'i do not know ' + asked
        ranked = sorted(merged, key=lambda u: -merged[u])
        return ('i was never taught ' + asked +
                ', but from how you used it, ' + asked +
                ' seems related to ' + join_values(ranked[:3]))

    # --- A9 relations, mirroring core.holy ---
    def _add_rel(self, s, p, o):
        if [s, p, o] not in self.rels:
            self.rels.append([s, p, o])

    def _drop_rels(self, key):
        self.rels = [e for e in self.rels if e[0] != key]

    def _learn_rel(self, key, value):
        v = lower_ascii(value)
        if v[:3] == 'in ' and len(v) > 3:
            self._add_rel(key, 'is-in', v[3:])
        if (v[:2] == 'a ' and len(v) > 2) or (v[:3] == 'an ' and len(v) > 3):
            self._add_rel(key, 'is-a', v)
        if v[:4] == 'has ' and len(v) > 4:
            self._add_rel(key, 'has', v[4:])
        for p, pred in (('อยู่ ', 'is-in'), ('คือ ', 'means'),
                        ('หมายความว่า ', 'means')):
            if v.startswith(p) and len(v) > len(p):
                self._add_rel(key, pred, v[len(p):])

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
                for e in self.rels:
                    if e[1] == pred and stripart(e[0]) == node:
                        queue.append((stripart(e[2]), path + [[e[0], e[2]]]))
        return None

    def _where_chain(self, start):
        node = stripart(start)
        path = []
        visited = set()
        while node not in visited and len(path) < 8:
            visited.add(node)
            found = None
            for e in self.rels:
                if e[1] == 'is-in' and stripart(e[0]) == node and found is None:
                    found = e
            if found is None:
                break
            path.append([found[0], found[2]])
            node = stripart(found[2])
        return path

    def _chain_reply(self, x, pred, y):
        path = self._chain(x, pred, y)
        if path is None:
            return 'not that i know'
        out = 'yes:'
        for s, o in path:
            if pred == 'is-in':
                out += ' ' + s + ' is in ' + o + ','
            if pred == 'is-a':
                out += ' ' + s + ' is ' + o + ','
        return out[:-1]

    def _where_reply(self, x, sep):
        path = self._where_chain(x)
        if not path:
            return self._recall(x)
        return ', '.join(s + sep + o for s, o in path)

    def _mean_reply(self, x, sep):
        defs = [e[2] for e in BUILTIN_RELS if e[0] == x]
        defs += [e[2] for e in self.rels if e[0] == x and e[1] == 'means']
        if defs:
            return x + sep + join_values(defs)
        return self._recall(x)

    def respond(self, line):
        text = normalize(line)
        if text and text[-1] in '?.':
            text = text[:-1]
        m = lower_ascii(text)
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
                return self._teach(mrest[:k], rest[k + 4:])
            k = mrest.find(' has ')
            if k > 0 and k + 5 < len(mrest):
                return unteach_is(self._teach_also(mrest[:k], rest[k + 1:]), 'has')
            k = mrest.find(' อยู่ ')
            if k > 0 and k + len(' อยู่ ') < len(mrest):
                return unteach_is(self._teach_also(mrest[:k], rest[k + 1:]), 'อยู่')
            k = mrest.find(' คือ ')
            if k > 0 and k + len(' คือ ') < len(mrest):
                return unteach_is(self._teach_also(mrest[:k], rest[k + 1:]), 'คือ')
            return 'i do not understand'
        if m[:10] == 'what does ' and len(m) > 15 and m[-5:] == ' mean':
            return self._mean_reply(m[10:-5], ' means ')
        if m[:3] == 'is ':
            rest3 = m[3:]
            k = rest3.find(' in ')
            if k > 0:
                return self._chain_reply(rest3[:k], 'is-in', rest3[k + 4:])
            k = rest3.find(' an ')
            if k > 0:
                return self._chain_reply(rest3[:k], 'is-a', rest3[k + 4:])
            k = rest3.find(' a ')
            if k > 0:
                return self._chain_reply(rest3[:k], 'is-a', rest3[k + 3:])
            return 'i do not understand'
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
            return 'i do not understand'
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
            self._add_rel(phrase, 'means', target)
            if target in self.facts:
                self.aliases[phrase] = target
            return 'ok, ' + phrase + means_p + target
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
        self._learn_rel(key, value)
        self._cooc_add(key, value)
        if key in self.order:
            return 'updated ' + key + ' is ' + value
        self.order.append(key)
        return 'remembered ' + key + ' is ' + value

    def _teach_also(self, key, value):
        self.topic = key
        self._learn_rel(key, value)
        if key not in self.facts:
            self.facts[key] = [value]
            self.order.append(key)
            self._cooc_add(key, value)
            return 'remembered ' + key + ' is ' + value
        if value in self.facts[key]:
            return 'i already know that ' + key + ' is ' + value
        self.facts[key].append(value)
        self._cooc_add(key, value)
        return 'added: ' + key + ' is ' + value

    def _recall(self, asked):
        key = self._resolve(asked)
        if key is not None:
            self.topic = key
            return 'i know ' + key + ' is ' + join_values(self.facts[key])
        cands, keys = self._candidates(asked)
        if len(cands) > 1:
            awords = cwords(asked)
            scored = sorted(range(len(cands)),
                            key=lambda i: -self._usage_score(cands[i], awords))
            cands = [cands[i] for i in scored]
            keys = [keys[i] for i in scored]
        if 0 < len(cands) <= 3:
            self.pending = {'cands': cands, 'keys': keys}
            return 'did you mean ' + ', '.join(cands) + '?'
        if len(cands) > 3:
            return 'i do not know ' + asked
        return self._usage_reply(asked)

    def _forget(self, key):
        if key not in self.facts:
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
        return 'forgot ' + key

    def _list_reply(self):
        n = len(self.order)
        if n == 0:
            return 'i know nothing yet'
        joined = ', '.join(self.order)
        if n == 1:
            return 'i know 1 thing: ' + joined
        return 'i know ' + str(n) + ' things: ' + joined

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
            if any(len(w) >= 3 and w not in STOP and
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
        elif r < 0.982:
            line = a9_line()
        elif r < 0.995:
            line = a10_line()
        else:
            line = rng.choice(GARBAGE)
        line = punctuate(line)
        lines.append(line)
    if rng.random() < 0.7:
        pos = rng.randrange(len(lines) + 1)
        lines[pos:pos] = list(rng.choice(A9_SCENARIOS + A10_SCENARIOS))
    replies = [oracle.respond(line) for line in lines]
    return lines, replies, oracle


sessions = [make_session() for _ in range(25)]

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
total = sum(len(replies) for _, replies, _ in sessions)
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
STORE_WANT = ('remembered alpha is one\nadded: alpha is two\n'
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
