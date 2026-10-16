#!/usr/bin/env python3
"""Cold flat-list ownership and mutable aliases, never native pointers."""
from pathlib import Path
import os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
passed=0
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);driver=d/'driver'
    build=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/cold_scalar_run.holy'),'-o',str(driver)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/cold_scalar_run.holy'),str(driver)])
    r=subprocess.run(build,env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-200:];passed+=1
    cases=[
      'items = [1, 2]\nother = items\nother[0] = 9\nappend(items, 3)\nprint len(other)\nprint items[0]\nprint other[-1]\n',
      'def mutate(a,n):\n  a[0] = n\n  append(a, n + 1)\n  return a\nx = [0]\ny = mutate(x, 19)\nprint x[0]\nprint y[1]\ny[0] = 7\nprint x[0]\n',
      'items = []\ni = 0\nwhile i < 100:\n  append(items, i * 2)\n  i = i + 1\nprint len(items)\nprint items[-1]\n',
      'print 19 if true else 999\nprint 999 if false else 23\n',
      'def f(x=[]):\n  append(x, 1)\n  return len(x)\nprint f()\nprint f()\n',
      'a = [true, false, null, 7]\nprint a[0]\nprint a[1]\nprint a[2]\nprint a[3]\n',
      'a = []\nadd = append\nsize = len\nadd(a, 19)\nprint size(a)\nprint a[0]\n',
      'print not []\nprint not [1]\na = []\nif a:\n  print 999\nelse:\n  print 23\n',
      'def len(x):\n  return 99\nprint len([1])\n',
    ]
    for body in cases:
        source=d/'target.holy';source.write_text(body)
        ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30)
        got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and not got.stderr and got.stdout==ref.stdout,(body,got.stdout,got.stderr,ref.stderr);passed+=1
    failures=[('a = [1]\nprint a[1]\n','index out of range'),('a = [1]\nprint a[-2]\n','index out of range'),('a = [1]\na[true] = 7\n','signed30-bit'),('a = []\nappend(a, [])\n','unsupported value'),('a = [[1]]\n','unsupported value'),('a = []\nprint a\n','unsupported value'),('a = []\nf = a\nf()\n','not callable'),('a = []\ni = 0\nwhile i < 4097:\n  append(a, i)\n  i = i + 1\n','exceeds4096'),('i = 0\nwhile i < 1025:\n  a = []\n  i = i + 1\n','allocation budget')]
    for body,reason in failures:
        source.write_text(body);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert got.returncode and reason.encode()in got.stderr,(body,got.stderr);passed+=1
    # Validation of an element/index must precede mutation of interpreter state.
    harness=d/'atomic.holy';harness.write_text('import normalize\nimport irbuild\nimport coldscalar\nm = irbuild.build_module(normalize.parse("a = [19]\\na[0] = []\\n"), "")\ns = coldscalar.create(m, 100)\ntry:\n  coldscalar.run(s)\nexcept:\n  print s[2]["a"]["items"][0]\nprint s[5]\nfor i in range(15):\n  coldscalar.charge(s, 4096, false)\ncoldscalar.charge(s, 4095, false)\ntry:\n  coldscalar.charge(s, 1, false)\nexcept:\n  print s[9]\n')
    exe=d/'atomic';r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'xbuild',str(harness),'-o',str(exe)],env=env,capture_output=True,timeout=60);assert not r.returncode,r.stderr
    r=subprocess.run([str(exe)],env=env,capture_output=True,timeout=30);assert not r.returncode and r.stdout==b'19\n0\n65536\n',(r.stdout,r.stderr);passed+=1
mode='Python-built native executor'if '--python-bootstrap'in sys.argv else 'seed-built native executor'
print(f'{passed}/{passed} cold flat-list ownership/alias gates ({mode}; no shared native objects)')
