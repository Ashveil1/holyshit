#!/usr/bin/env python3
"""agent/core.holy conversation corpus vs an independent Python oracle.

Randomized sessions over the full command surface (remember / recall and
its aliases / association recall / topic follow-ups / session notes /
list / say / help / garbage) run through agent.core.respond; transcripts
(replies + final memory dump) must match the oracle byte for byte on
every hosted execution route, and agent/store.holy save/load roundtrips
are checked on the reference route (session state must NOT persist).
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

HELP = ("commands: remember <thing> is <fact> | what is <thing> | "
        "do you know <thing> | what do you know about <thing> | "
        "what about it | forget <thing> | forget it | note <text> | "
        "notes | clear notes | list | say <text> | help")
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


class Oracle:
    """Fresh reference implementation of the agent.core spec."""

    def __init__(self):
        self.facts = {}
        self.order = []
        self.notes = []
        self.topic = None

    def respond(self, line):
        text = normalize(line)
        if text and text[-1] in '?.':
            text = text[:-1]
        m = lower_ascii(text)
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
        if m == 'forget it':
            if self.topic is None:
                return 'i have no topic yet'
            return self._forget(self.topic)
        if m[:23] == 'what do you know about ':
            return self._about_reply(m[23:])
        if m[:9] == 'remember ':
            rest = text[9:]
            mrest = m[9:]
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
        return 'i do not understand'

    def _teach(self, key, value):
        self.topic = key
        if key in self.facts:
            self.facts[key] = value
            return 'updated ' + key + ' is ' + value
        self.facts[key] = value
        self.order.append(key)
        return 'remembered ' + key + ' is ' + value

    def _recall(self, key):
        if key in self.facts:
            self.topic = key
            return 'i know ' + key + ' is ' + self.facts[key]
        return 'i do not know ' + key

    def _forget(self, key):
        if key not in self.facts:
            return 'i do not know ' + key
        del self.facts[key]
        self.order.remove(key)
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

    def _about_reply(self, key):
        if key not in self.facts:
            return 'i do not know ' + key
        self.topic = key
        reply = 'i know ' + key + ' is ' + self.facts[key]
        words = lower_ascii(self.facts[key]).split(' ')
        for k in self.order:
            if k == key:
                continue
            kwords = lower_ascii(self.facts[k]).split(' ')
            if any(len(w) >= 3 and w not in STOP and w in kwords for w in words):
                reply += '; also ' + k + ' is ' + self.facts[k]
        return reply

    def _notes_reply(self):
        n = len(self.notes)
        if n == 0:
            return 'no notes yet'
        return '; '.join('note ' + str(i + 1) + ': ' + note
                         for i, note in enumerate(self.notes))


rng = random.Random(20261121)

KEYS = ['paris', 'milo', '曼谷', 'ไทย', 'café', 'x', 'my cat', 'a=b',
        'Tokyo', 'the answer', 'z', 'felix']
# Overlapping content words across values exercise association recall.
VALUES = ['nice', 'a cat', 'a big cat', 'likes fish', 'a dog', 'blue fish',
          'ประเทศไทย', '42', 'a City in France', 'ไม่รู้', 'x is y',
          'blue green', 'nothing much']
GARBAGE = ['', '   ', 'xyzzy', 'remember', 'remember x', 'remember is y',
           'what', 'what is', 'what is ', 'forget', 'say', 'say ',
           'remember x is', 'REMEMBER x IS ', 'hello there', '?', '.',
           'note', 'what do you know about', 'who is', 'where is']
ALIASES = ['do you know', 'tell me about', 'who is', 'where is']


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
    for _ in range(40):
        r = rng.random()
        if r < 0.24:
            key = rng.choice(KEYS)
            value = rng.choice(VALUES)
            line = mangle('remember') + ' ' + mangle(key) + ' ' + \
                mangle('is') + ' ' + value
        elif r < 0.37:
            line = mangle('what is') + ' ' + mangle(rng.choice(KEYS))
        elif r < 0.46:
            line = mangle(rng.choice(ALIASES)) + ' ' + mangle(rng.choice(KEYS))
        elif r < 0.54:
            line = mangle('what do you know about') + ' ' + mangle(rng.choice(KEYS))
        elif r < 0.60:
            line = mangle('what about it')
        elif r < 0.66:
            line = mangle('forget') + ' ' + mangle(rng.choice(KEYS + ['ghost']))
        elif r < 0.70:
            line = mangle('forget it')
        elif r < 0.78:
            line = mangle('note') + ' ' + rng.choice(VALUES + ['Mixed CASE note'])
        elif r < 0.83:
            line = mangle('notes')
        elif r < 0.86:
            line = mangle('clear notes')
        elif r < 0.91:
            line = mangle('list')
        elif r < 0.95:
            line = mangle('say') + ' ' + rng.choice(VALUES + ['Mixed CASE text'])
        elif r < 0.97:
            line = mangle('help')
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
        expected_lines.append(k + ' => ' + oracle.facts[k])
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
text += '    print k + " => " + state["facts"][k]\n'
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
print agent.core.respond(s, "remember beta is two")
print agent.core.respond(s, "note buy milk")
agent.store.save(s, p)
s2 = agent.store.load(p)
print agent.core.respond(s2, "what is alpha")
print agent.core.respond(s2, "list")
print agent.core.respond(s2, "notes")
print agent.core.respond(s2, "what about it")
print agent.core.respond(s2, "forget alpha")
agent.store.save(s2, p)
s3 = agent.store.load(p)
print agent.core.respond(s3, "list")
'''
STORE_WANT = ('remembered alpha is one\nremembered beta is two\nnoted\n'
              'i know alpha is one\ni know 2 things: alpha, beta\n'
              'no notes yet\ni know alpha is one\n'
              'forgot alpha\ni know 1 thing: beta\n')

FRESH_PROG = '''import agent.core
import agent.store
s = agent.core.new_state()
print agent.core.respond(s, "list")
s2 = agent.store.load({path})
print agent.core.respond(s2, "list")
'''

# A file in the original v0.1 on-disk shape (facts + order only) must
# still load, with session state starting empty.
V01_PROG = '''import agent.core
import agent.store
s = agent.store.load({path})
print agent.core.respond(s, "what is a")
print agent.core.respond(s, "list")
print agent.core.respond(s, "notes")
print agent.core.respond(s, "what about it")
'''
V01_WANT = ('i know a is 1\ni know 1 thing: a\nno notes yet\n'
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
        # v0.1 on-disk format still loads.
        v01 = d/'v01.json'
        v01.write_text('{"facts": {"a": "1"}, "order": ["a"]}', encoding='utf-8')
        vprog = d/'v01.holy'
        vprog.write_text(V01_PROG.format(path=lit(str(v01))), encoding='utf-8')
        r = run_ref(vprog)
        assert r.returncode == 0 and r.stdout == V01_WANT, (r.returncode,
                                                            r.stdout, r.stderr[-500:])
    print('ok agent.store roundtrip + 4 fresh-load cases + v0.1-format load (reference route)', flush=True)


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
