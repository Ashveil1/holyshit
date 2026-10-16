#!/usr/bin/env python3
"""Self-hosted IR execution, not eager native compilation of the target."""
from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
passed=0
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);driver=d/'driver'
    build=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/cold_scalar_run.holy'),'-o',str(driver)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/cold_scalar_run.holy'),str(driver)])
    r=subprocess.run(build,env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-250:];passed+=1
    cases=[(ROOT/'tests/fib.holy').read_text(),
      's = 0\ni = 0\nwhile i < 100:\n  i = i + 1\n  if i == 4:\n    continue\n  if i == 25:\n    break\n  s = s + i\nprint s\n',
      'def f(x):\n  if x < 0:\n    return -x\n  elif x == 0:\n    return 19\n  return x * 2\nprint f(-7)\nprint f(0)\nprint f(9)\n',
      'counter = 0\ndef f(n):\n  global counter\n  counter = counter + n\n  return counter\nprint f(3)\nprint f(4)\n',
      'def no():\n  print 999\n  return 1\nprint false and no()\nprint true or no()\n',
      'def g(n):\n  return n + 100\ndef start(n):\n  global f\n  f = g\n  return n\nf = start\nprint f(1)\nprint f(3)\n',
      'print true and false\nprint false or 9\nprint not null\nprint null\nprint true == 1\nprint false != 0\n',
      'def f(x):\n  if x < 2:\n    return x\n  return g(x - 1)\ndef g(x):\n  return f(x)\nprint f(7)\n',
    ]
    for text in cases:
        source=d/'target.holy';source.write_text(text)
        ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30)
        got=subprocess.run([str(driver),str(source),'--stats'],env=env,capture_output=True,timeout=30)
        assert not got.returncode and not got.stderr and not ref.returncode,(text,got.stdout,got.stderr,ref.stderr)
        out,marker,tail=got.stdout.partition(b'COLD SCALAR STATS ');assert marker and out==ref.stdout,(out,ref.stdout)
        steps,counts=json.loads(tail);assert 0<steps<=1000000 and counts['<main>']==1 and all(x>=0 for x in counts.values());passed+=1
        if text==cases[0]:assert counts['fib$L1']==2150,counts;passed+=1
    for body in ['print 9\nprint "unsupported"\n','print 9\nprint [1]\n','print 9\nprint 1 / 2\n','print 9\ntry:\n  pass\nexcept:\n  pass\n','print 9\ndef outer():\n  def inner():\n    return 1\n  return inner\n','print 9\nimport std.math\n']:
        source.write_text(body);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert got.returncode and not got.stdout,(body,got.stdout,got.stderr);passed+=1
    for body,reason in [('print 536870911 + 1\n','signed30-bit'),('def f():\n  return f()\nf()\n','call depth'),('x = 7\ndef f():\n  print x\n  x = 1\nf()\n','unbound local'),('f = 1\nf()\n','not callable')]:
        source.write_text(body);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert got.returncode and reason.encode()in got.stderr,(body,got.stderr);passed+=1
    # Library-level tiny budget, handler cleanup and no accidental second run.
    harness=d/'budget.holy';harness.write_text('import normalize\nimport irbuild\nimport coldscalar\nm = irbuild.build_module(normalize.parse("while true:\\n  pass\\n"), "")\ns = coldscalar.create(m, 100)\ntry:\n  coldscalar.run(s)\nexcept as e:\n  print e\nprint s[3]\nprint s[5]\ntry:\n  coldscalar.run(s)\nexcept as e:\n  print e\n')
    exe=d/'budget';r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'xbuild',str(harness),'-o',str(exe)],env=env,capture_output=True,timeout=60);assert not r.returncode,r.stderr
    r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=30)
    assert not r.returncode and 'instruction budget exhausted'in r.stdout and '\n100\n0\n'in r.stdout and 'state already started'in r.stdout,(r.stdout,r.stderr);passed+=1
mode='Python-built native executor'if '--python-bootstrap'in sys.argv else 'seed-built native executor'
print(f'{passed}/{passed} self-hosted cold scalar IR gates ({mode}; no target codegen or hot tier)')
