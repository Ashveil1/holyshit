#!/usr/bin/env python3
"""Self-hosted counters match reference events, remain bounded and opt-in."""
from pathlib import Path
import contextlib
import io
import json
import os
import platform
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import interp
import ir
from irprofile import ExecutionProfile
ENV = dict(os.environ, HSPATH=f'{ROOT}/selfhost:{ROOT}/selfhost/be', HSROOT=str(ROOT))
BUILD = ([sys.executable, str(ROOT/'a64build.py')] if platform.machine() in ('arm64','aarch64')
         else [str(ROOT/'bootstrap/hs-hosted-x86_64')])

def command(args):
    return subprocess.run([str(x) for x in args], env=ENV, capture_output=True, timeout=600)

def sites(p):
    return sorted(p['sites'], key=lambda s:(s['function'],s['kind'],s['label']))

sources = [
 'def f(x):\n  return x\ni = 0\nwhile i < 5:\n  print f(i)\n  i = i + 1\nprint f("secret text")\nprint f(true)\n',
 'def f(n):\n  if n < 1:\n    return 1\n  return f(n - 1) + 1\nprint f(6)\n',
 'def outer(x):\n  def inner(y):\n    return x + y\n  return inner\nf = outer(3)\nprint f(4)\n',
 'try:\n  raise "x"\nexcept:\n  print "caught"\nfinally:\n  print "done"\n',
 'print "before"\nprint 1 / 0\n',
]
passed = 0
with tempfile.TemporaryDirectory(prefix='hs-irprofile.') as d:
    d = Path(d)
    exe = d/'runner'
    r = command(BUILD+[ROOT/'selfhost/be/irprofile_run.holy',exe])
    assert r.returncode == 0, r.stderr
    for source in sources:
        interp.reset_parse_state()
        module = ir.build_module(interp.parse_program(source))
        for capacity in (1,1024):
            profile = ExecutionProfile(capacity)
            output = io.StringIO()
            error = None
            with contextlib.redirect_stdout(output):
                try:
                    ir.run_module(module, str(d), profile=profile)
                except interp.HSErr as e:
                    error = e
            src, dest = d/'case.holy', d/'profile.json'
            src.write_text(source)
            r = command([exe,src,dest,capacity])
            assert r.stdout.decode() == output.getvalue(), (source,r.stdout,r.stderr)
            assert bool(r.returncode) == bool(error), (source,r.stderr)
            p = json.loads(dest.read_text())
            ref = profile.snapshot()
            assert p['mode'] == 'hs-ir-profile-not-jit'
            assert sites(p) == sites(ref), (sites(p),sites(ref))
            assert p['dropped_events'] == ref['dropped_events']
            assert len(p['sites']) <= capacity
            assert 'secret text' not in dest.read_text()
            passed += 1
    unit = d/'unit.holy'
    unit.write_text('''import irprofile
p = irprofile.create(1)
irprofile.record(p, "f", "entry", "", ["T0"])
i = 1
while i < 12:
  irprofile.record(p, "f", "entry", "", ["T" + str(i)])
  i = i + 1
s = irprofile.snapshot(p)
assert len(s["sites"][0]["argument_types"]) == 8
assert s["sites"][0]["megamorphic"]
s["sites"][0]["argument_types"][0][0] = "changed"
assert irprofile.snapshot(p)["sites"][0]["argument_types"][0][0] == "T0"
k = p["order"][0]
p["sites"][k]["count"] = 2147483647
irprofile.record(p, "f", "entry", "", null)
assert p["sites"][k]["count"] == 2147483647
p["dropped_events"] = 2147483647
irprofile.record(p, "g", "block", "b", null)
assert p["dropped_events"] == 2147483647
for x in [0, 65537, true, 1.5]:
  rejected = false
  try:
    irprofile.create(x)
  except:
    rejected = true
  assert rejected
print "ok"
''')
    r = command(BUILD+[unit,d/'unit'])
    assert r.returncode == 0, r.stderr
    r = command([d/'unit'])
    assert r.returncode == 0 and r.stdout == b'ok\n', (r.stdout,r.stderr)
    passed += 1
print(f'{passed}/{passed} hs IR profiling gates (not a JIT tier)')
