#!/usr/bin/env python3
"""Opt-in counters preserve semantics, bound storage and clear on errors."""
from pathlib import Path
import contextlib,io,json,sys,subprocess,tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import interp,ir
from irprofile import ExecutionProfile
passed=0

def module(source):
    interp.reset_parse_state()
    return ir.build_module(interp.parse_program(source))

def execute(m,profile=None):
    out=io.StringIO();err=None
    with contextlib.redirect_stdout(out):
        try:ir.run_module(m,profile=profile)
        except interp.HSErr as e:err=(e.msg,e.line)
    return out.getvalue(),err

src='def f(x):\n  return x\ni = 0\nwhile i < 5:\n  print f(i)\n  i = i + 1\nprint f("secret text")\nprint f(true)\n'
m=module(src);p=ExecutionProfile();assert execute(m)==execute(m,p);passed+=1
with tempfile.TemporaryDirectory() as d:
    path=Path(d)/'profile.holy';path.write_text(src)
    reference=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(path)],capture_output=True)
    assert reference.returncode==0 and reference.stderr==b'' and reference.stdout.decode()==execute(m)[0]
    passed+=1
snap=p.snapshot();entries=[s for s in snap['sites'] if s['kind']=='entry'];f=next(s for s in entries if s['function'].startswith('f$'));assert f['count']==7 and f['argument_types']==[['Int'],['Str'],['Bool']];passed+=1
assert max(s['count'] for s in snap['sites'] if s['kind']=='block')>=6;passed+=1
assert 'secret text' not in json.dumps(snap);passed+=1
snap['sites'][0]['count']=999;assert p.snapshot()['sites'][0]['count']!=999;f['argument_types'][0][0]='changed';assert 'changed' not in json.dumps(p.snapshot());passed+=1
small=ExecutionProfile(1);execute(m,small);assert len(small.sites)==1 and small.dropped_events>0;passed+=1
# Saturation and type diversity are deterministic independent of target loops.
key=('probe','entry','');p._record(key,['T0'])
for i in range(1,12):p._record(key,['T'+str(i)])
assert len(p.sites[key]['argument_types'])==8 and p.sites[key]['megamorphic'];p.sites[key]['count']=2147483647;p._record(key);assert p.sites[key]['count']==2147483647;passed+=1
bad=module('print "before"\nprint 1 / 0\n');assert execute(bad)==execute(bad,p);assert ir._PROFILE is None;passed+=1
count=json.dumps(p.snapshot());execute(m);assert json.dumps(p.snapshot())==count;passed+=1
for source in ['def f(n):\n  if n < 1:\n    return 1\n  return f(n - 1) + 1\nprint f(4)\n','try:\n  raise "x"\nexcept:\n  print "caught"\nfinally:\n  print "done"\n','def outer(x):\n  def inner(y):\n    return x + y\n  return inner\nf = outer(3)\nprint f(4)\n']:
    test=module(source);assert execute(test)==execute(test,ExecutionProfile());passed+=1
for value in [0,65537,True,1.5]:
    try:ExecutionProfile(value)
    except ValueError:passed+=1
    else:raise AssertionError('invalid site capacity accepted')
print(f'{passed}/{passed} opt-in reference IR profiling gates (not a JIT tier)')
