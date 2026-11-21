#!/usr/bin/env python3
"""agent/core.holy conversation corpus vs an independent Python oracle.

Randomized sessions of remember/what is/forget/list/say/help/unknown ops
run through agent.core.respond; transcripts (replies + final memory dump)
must match the oracle byte for byte on every hosted execution route, and
agent/store.holy save/load roundtrips are checked on the reference route.
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
        "forget <thing> | list | say <text> | help")
WS = ' \t\n\r'


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

    def respond(self, line):
        text = normalize(line)
        m = lower_ascii(text)
        if m == 'help':
            return HELP
        if m == 'list':
            return self._list_reply()
        if m[:9] == 'remember ':
            rest = text[9:]
            mrest = m[9:]
            k = mrest.find(' is ')
            if k > 0 and k + 4 < len(mrest):
                return self._teach(mrest[:k], rest[k + 4:])
            return 'i do not understand'
        if m[:8] == 'what is ':
            key = m[8:]
            if key in self.facts:
                return 'i know ' + key + ' is ' + self.facts[key]
            return 'i do not know ' + key
        if m[:7] == 'forget ':
            return self._forget(m[7:])
        if m[:4] == 'say ' and len(text) > 4:
            return text[4:]
        return 'i do not understand'

    def _teach(self, key, value):
        if key in self.facts:
            self.facts[key] = value
            return 'updated ' + key + ' is ' + value
        self.facts[key] = value
        self.order.append(key)
        return 'remembered ' + key + ' is ' + value

    def _forget(self, key):
        if key not in self.facts:
            return 'i do not know ' + key
        del self.facts[key]
        self.order.remove(key)
        return 'forgot ' + key

    def _list_reply(self):
        n = len(self.order)
        if n == 0:
            return 'i know nothing yet'
        joined = ', '.join(self.order)
        if n == 1:
            return 'i know 1 thing: ' + joined
        return 'i know ' + str(n) + ' things: ' + joined


rng = random.Random(20261121)

KEYS = ['paris', 'milo', '曼谷', 'ไทย', 'café', 'x', 'my cat', 'a=b',
        'Tokyo', 'the answer', 'z']
VALUES = ['nice', 'a cat', 'ประเทศไทย', '42', 'a City in France', 'ไม่รู้',
          'x is y', 'blue green', 'nothing much']
GARBAGE = ['', '   ', 'xyzzy', 'remember', 'remember x', 'remember is y',
           'what', 'what is', 'what is ', 'forget', 'say', 'say ',
           'remember x is', 'REMEMBER x IS ', 'hello there']


def mangle(word):
    # Random ASCII case + whitespace mangling; meaning must not change.
    s = ''.join(c.upper() if rng.random() < 0.4 else c for c in word)
    if rng.random() < 0.3:
        s = ' ' * rng.randrange(1, 3) + s
    if rng.random() < 0.3:
        s = s + rng.choice([' ', '  ', '\t']) * rng.randrange(1, 2)
    return s


def make_session():
    oracle = Oracle()
    known = []
    lines = []
    replies = []
    for _ in range(35):
        r = rng.random()
        if r < 0.35:
            key = rng.choice(KEYS)
            value = rng.choice(VALUES)
            line = mangle('remember') + ' ' + mangle(key) + ' ' + \
                mangle('is') + ' ' + value
            if rng.random() < 0.5:
                known.append(lower_ascii(normalize(key)))
        elif r < 0.60:
            key = rng.choice(KEYS)
            line = mangle('what is') + ' ' + mangle(key)
        elif r < 0.72:
            key = rng.choice(KEYS + ['ghost'])
            line = mangle('forget') + ' ' + mangle(key)
        elif r < 0.82:
            line = mangle('list')
        elif r < 0.90:
            line = mangle('say') + ' ' + rng.choice(VALUES + ['Mixed CASE text'])
        elif r < 0.95:
            line = mangle('help')
        else:
            line = rng.choice(GARBAGE)
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
text += 'print "total " + str(total)\n'

STORE_PROG = '''import agent.core
import agent.store
p = {path}
s = agent.core.new_state()
print agent.core.respond(s, "remember alpha is one")
print agent.core.respond(s, "remember beta is two")
agent.store.save(s, p)
s2 = agent.store.load(p)
print agent.core.respond(s2, "what is alpha")
print agent.core.respond(s2, "list")
print agent.core.respond(s2, "forget alpha")
agent.store.save(s2, p)
s3 = agent.store.load(p)
print agent.core.respond(s3, "list")
'''
STORE_WANT = ('remembered alpha is one\nremembered beta is two\n'
              'i know alpha is one\ni know 2 things: alpha, beta\n'
              'forgot alpha\ni know 1 thing: beta\n')

FRESH_PROG = '''import agent.core
import agent.store
s = agent.core.new_state()
print agent.core.respond(s, "list")
s2 = agent.store.load({path})
print agent.core.respond(s2, "list")
'''


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
    print('ok agent.store save/load roundtrip + 4 fresh-load cases (reference route)', flush=True)


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
