#!/usr/bin/env python3
"""Optional hs formatter comment mode matches the established Python oracle."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import fmt
import interp

ENV = dict(os.environ, HSROOT=str(ROOT), HSPATH=str(ROOT / 'selfhost'))
CASES = {
    'empty': '',
    'comment-only': '# first\n// final',
    'simple': '# header\nx=1 # x\nprint x // result\n# end',
    'crlf': '# header\r\nx=1 # x\r\nprint x\r\n# end\r\n',
    'strings': 'print "hash # slash // quote \\\" tail" # real\nprint "\\\\" // slash\n',
    'unicode': '# ไทย café 😀\u3000\nx = "ไทย # // 😀" # café\u00a0\nprint x\n',
    'branch': '# top\nif true: # if\n  print 1 # one\n# before else\nelse: # else\n  print 2\n# final\n',
    'try': 'try: # try\n  raise "x" # raise\n# before except\nexcept as e: # except\n  print "caught" # caught\nfinally: # finally\n  print "done" # done\n',
    'loop': 'for x in [1, 2]: # loop\n  if x == 1: # if\n    print x # print\n  elif x == 2: # elif\n    print 2\nwhile false: # while\n  pass\n',
    'lambda': '# top\nf = lambda x: x + 1 # lambda\nprint f(1)\n',
    'class': 'class A: # cls\n  # method\n  def f(self): # meth\n    return 1 # ret\nprint 0\n',
    'extern': 'extern: # ext\n  I64 puts(Str s) # sig\nprint 0\n',
    'struct': 'unsafe:\n  struct X: # st\n    I64 x # field\nprint 0\n',
    'existing-comments': (ROOT / 'tests/fmt_comments.holy.txt').read_text(),
}
# Exercise every Python whitespace suffix, without assuming byte == codepoint.
# Individual CR suffixes and CRLF are covered separately: interp.read_text
# normalizes embedded CR, whereas native read_text preserves those bytes.
WS = ''.join(chr(i) for i in range(sys.maxunicode + 1) if chr(i).isspace())
CASES['individual-whitespace'] = ''.join('# suffix' + w + '\n' for w in WS) + 'print 1\n'
CASES['all-whitespace'] = '# trimmed' + WS.replace('\n', '').replace('\r', '') + '\nprint 1 # end' + WS.replace('\n', '').replace('\r', '') + '\n'
# Literal controls remain unchanged rather than becoming unsupported escapes.
controls = ''.join(chr(i) for i in range(32)) + chr(127)
def literal(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t').replace('\0', '\\0') + '"'
CASES['controls'] = 's = ' + literal(controls) + ' # control bytes\nprint s\n'
PINNED = {
    'branch': '# top\nif true:  # if\n  print 1  # one\nelse:\n  # before else\n  print 2\n# final\n# else\n',
    'class': 'class A:  # cls\n  def f(self):\n    # method\n    return 1  # ret\nprint 0\n# meth\n',
    'extern': 'extern:  # ext\n  I64 puts(Str s)\nprint 0\n# sig\n',
    'struct': 'unsafe:\n  struct X:  # st\n    I64 x\nprint 0\n# field\n',
}
passed = failed = 0

def check(ok, label):
    global passed, failed
    passed += bool(ok)
    failed += not ok
    print(('ok  ' if ok else 'FAIL'), label, flush=True)

def run(cmd, **kwargs):
    return subprocess.run(cmd, env=ENV, capture_output=True, timeout=120, **kwargs)

def oracle(src, comments):
    interp.reset_parse_state()
    ast = interp.parse_program(src, raw=True)
    return fmt.fmt_program_c(ast, src) if comments else fmt.fmt_program(ast)

with tempfile.TemporaryDirectory(prefix='hs fmt comments ') as temp:
    d = Path(temp)
    native = d / 'native formatter'
    direct = d / 'x64 formatter'
    for label, cmd in [
        ('native-hs', [str(ROOT / 'bootstrap/hs-hosted-x86_64'), str(ROOT / 'selfhost/fmt.holy'), str(native)]),
        ('x64', [sys.executable, str(ROOT / 'hs.py'), 'xbuild', str(ROOT / 'selfhost/fmt.holy'), '-o', str(direct)]),
    ]:
        r = run(cmd)
        check(r.returncode == 0, 'build ' + label + ' ' + r.stderr.decode(errors='replace')[-200:])
        if r.returncode:
            sys.exit(1)
    routes = {
        'interp': [sys.executable, str(ROOT / 'interp.py'), str(ROOT / 'selfhost/fmt.holy')],
        'x64': [str(direct)],
        'native-hs': [str(native)],
    }
    for name, src in CASES.items():
        path = d / (name + '.holy')
        path.write_bytes(src.encode())
        expected = oracle(src, True)
        if name in PINNED:
            check(expected == PINNED[name], name + ' pins reference relocation behavior')
        check(oracle(expected, True) == expected, name + ' reference idempotence')
        for label, cmd in routes.items():
            for comments in (False, True):
                opts = ['--comments'] if comments else []
                r = run(cmd + [str(path)] + opts)
                want = expected if comments else oracle(src, False)
                check(r.returncode == 0 and not r.stderr and r.stdout == want.encode(),
                      f'{name} {label} {"comments" if comments else "default"} exact bytes ' +
                      (repr((r.returncode, r.stdout, r.stderr)) if r.returncode or r.stdout != want.encode() else ''))
                if comments:
                    formatted = d / 'second.holy'
                    formatted.write_bytes(r.stdout)
                    again = run(cmd + [str(formatted), '--comments'])
                    check(again.returncode == 0 and not again.stderr and again.stdout == r.stdout,
                          f'{name} {label} comment-mode idempotence')
        # Programs without unsafe/extern can execute on the reference route.
        # Compare behavior, not stderr source locations on errors.
        if name not in ('extern', 'struct'):
            formatted = d / 'output.holy'
            formatted.write_bytes(expected.encode())
            before = run([sys.executable, str(ROOT / 'interp.py'), str(path)])
            after = run([sys.executable, str(ROOT / 'interp.py'), str(formatted)])
            check(before.returncode == after.returncode == 0 and before.stdout == after.stdout,
                  name + ' program output preserved')
    # Installed-style native invocation needs no compiler/Python or import data.
    isolated = dict(ENV, PATH=str(d / 'absent-path'), HSROOT=str(d), HSPATH=str(d))
    path = d / 'native-only.holy'
    path.write_text('# native comment\nprint 7 # result\n')
    r = subprocess.run([str(native), str(path), '--comments'], env=isolated,
                       capture_output=True, timeout=30)
    check(r.returncode == 0 and not r.stderr and r.stdout == oracle(path.read_text(), True).encode(),
          'native formatter invocation without checkout/Python/gcc PATH')
    # Mode must never mutate the source; unrelated extra args retain old behavior.
    path = d / 'extra.holy'
    src = b'print 1 # retained only on request\n'
    path.write_bytes(src)
    for label, cmd in routes.items():
        plain = run(cmd + [str(path)])
        extra = run(cmd + [str(path), '--unrelated'])
        check(plain.returncode == extra.returncode == 0 and plain.stdout == extra.stdout,
              label + ' unrelated extra argument remains structural')
        run(cmd + [str(path), '--comments'])
        check(path.read_bytes() == src, label + ' source bytes unchanged')
        broken = d / 'invalid.holy'
        broken.write_text('def broken(:\n')
        old = run(cmd + [str(broken)])
        new = run(cmd + [str(broken), '--comments'])
        check(old.returncode != 0 and (old.returncode, old.stdout, old.stderr) == (new.returncode, new.stdout, new.stderr),
              label + ' parse error behavior unchanged')
print(f'{passed}/{passed + failed} hs formatter comment gates')
sys.exit(bool(failed))
