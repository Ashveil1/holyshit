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
        "<fact> | no, <thing> is <fact> | what is <thing> | "
        "do you know <thing> | what do you know about <thing> | "
        "how is <thing> | how about <thing> | <thing> คืออะไร | "
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
            return 'i do not understand'
        if m[:8] == 'what is ':
            return self._recall(m[8:])
        if m[:12] == 'do you know ':
            return self._recall(m[12:])
        if m[:15] == 'tell me about ':
            return self._recall(m[15:])
        if m[:7] == 'who is ':
            return self._recall(m[7:])
        if m[:9] == 'where is ':
            return self._recall(m[9:])
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
        k = m.find(' means ')
        if k > 0 and k + 7 < len(m):
            phrase = m[:k]
            target = m[k + 7:]
            if phrase == target:
                return 'i do not understand'
            if target in self.facts:
                self.aliases[phrase] = target
                return 'ok, ' + phrase + ' means ' + target
            return 'i do not know ' + target
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
        self.facts[key] = [value]
        if key in self.order:
            return 'updated ' + key + ' is ' + value
        self.order.append(key)
        return 'remembered ' + key + ' is ' + value

    def _teach_also(self, key, value):
        self.topic = key
        if key not in self.facts:
            self.facts[key] = [value]
            self.order.append(key)
            return 'remembered ' + key + ' is ' + value
        if value in self.facts[key]:
            return 'i already know that ' + key + ' is ' + value
        self.facts[key].append(value)
        return 'added: ' + key + ' is ' + value

    def _recall(self, asked):
        key = self._resolve(asked)
        if key is not None:
            self.topic = key
            return 'i know ' + key + ' is ' + join_values(self.facts[key])
        cands, keys = self._candidates(asked)
        if 0 < len(cands) <= 3:
            self.pending = {'cands': cands, 'keys': keys}
            return 'did you mean ' + ', '.join(cands) + '?'
        return 'i do not know ' + asked

    def _forget(self, key):
        if key not in self.facts:
            return 'i do not know ' + key
        del self.facts[key]
        self.order.remove(key)
        self.aliases = {a: t for a, t in self.aliases.items() if t != key}
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
        elif r < 0.945:
            line = mangle('say') + ' ' + rng.choice(VALUES + ['Mixed CASE text'])
        elif r < 0.95:
            line = mangle('help')
        elif r < 0.99:
            line = a8_line()
        else:
            line = rng.choice(GARBAGE)
        line = punctuate(line)
        lines.append(line)
        replies.append(oracle.respond(line))
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
agent.store.save(s, p)
s2 = agent.store.load(p)
print agent.core.respond(s2, "what is alpha")
print agent.core.respond(s2, "what is a1")
print agent.core.respond(s2, "list")
print agent.core.respond(s2, "notes")
print agent.core.respond(s2, "forget alpha")
print agent.core.respond(s2, "what is a1")
agent.store.save(s2, p)
s3 = agent.store.load(p)
print agent.core.respond(s3, "list")
'''
STORE_WANT = ('remembered alpha is one\nadded: alpha is two\n'
              'ok, a1 means alpha\nnoted\n'
              'i know alpha is one and two\ni know alpha is one and two\n'
              'i know 1 thing: alpha\nno notes yet\nforgot alpha\n'
              'i do not know a1\ni know nothing yet\n')

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
    print('ok agent.store roundtrip + 4 fresh-load cases + pre-v3 migration (reference route)', flush=True)


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
