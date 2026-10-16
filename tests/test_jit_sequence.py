#!/usr/bin/env python3
"""Fresh native runtimes alternate success/error in one driver, unmap per cycle."""
from pathlib import Path
import json,os,signal,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
def alarm(_s,_f):raise TimeoutError('sequence checkpoint stalled')
signal.signal(signal.SIGALRM,alarm)
passed=0
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);driver=d/'driver'
    build=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/jit_sequence_probe.holy'),'-o',str(driver)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/jit_sequence_probe.holy'),str(driver)])
    r=subprocess.run(build,env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-250:];passed+=1
    module=d/'isolated.holy';module.write_text('value = []\nappend(value, 19)\n')
    healthy=d/'healthy.holy';healthy.write_text('import isolated\nappend(isolated.value, 23)\nprint isolated.value\n')
    error=d/'error.holy';error.write_text('items = []\nfor i in range(10000):\n  append(items, str(i))\ntry:\n  raise "sequence error " + str(len(items))\nfinally:\n  print "unwound"\n')
    empty=d/'empty.holy';empty.write_text('pass\n')
    sources=[healthy,error,healthy,ROOT/'tests/t_closure.holy',error,ROOT/'tests/x64/gc_stress.holy',healthy,empty]
    refs=[subprocess.run([sys.executable,str(ROOT/'interp.py'),str(s)],env=env,capture_output=True,timeout=60)for s in sources]
    p=subprocess.Popen([str(driver),'--checkpoints',*map(str,sources)],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        def mapped(address):
            return any(int(row.split('-')[0],16)<=address<int(row.split()[0].split('-')[1],16)for row in Path(f'/proc/{p.pid}/maps').read_text().splitlines())
        def proceed():p.stdin.write('\n');p.stdin.flush()
        for index,ref in enumerate(refs):
            signal.alarm(60)
            line=p.stdout.readline();prefix=f'JIT SEQUENCE IMAGE {index} '
            assert line.startswith(prefix),line
            image,size=json.loads(line[len(prefix):]);assert image>0 and size>0
            output=[]
            while True:
                line=p.stdout.readline();assert line,('checkpoint EOF',p.poll())
                if line.startswith('JIT OWNED RANGES '):break
                output.append(line)
            assert ''.join(output).encode()==ref.stdout,(index,output,ref.stdout)
            ranges=json.loads(line[len('JIT OWNED RANGES '):])
            assert mapped(image)and mapped(image+size-1)and all(mapped(base)and mapped(base+length-1)for base,length in ranges);passed+=1
            proceed();assert p.stdout.readline()=='JIT HEAP UNMAPPED\n'
            assert not any(mapped(base)or mapped(base+length-1)for base,length in ranges)and mapped(image);passed+=1
            proceed();line=p.stdout.readline();prefix=f'JIT SEQUENCE OUTCOME {index} ';assert line.startswith(prefix),line
            status,error=json.loads(line[len(prefix):]);assert status==int(bool(ref.returncode))
            if status:
                msg,ln=error;assert ref.stderr==('error: '+msg+(' at line '+str(ln)if ln else '')+'\n').encode(),(index,error,ref.stderr)
            else:assert error is None and not ref.stderr
            line=p.stdout.readline();assert line.startswith(f'JIT SEQUENCE RELEASED {index} ')and line.endswith(' false\n'),line
            assert not mapped(image)and not mapped(image+size-1);passed+=1
            proceed()
        out,err=p.communicate(timeout=20);assert not p.returncode and not err and out==f'JIT SEQUENCE DONE {len(sources)}\n',(out,err);passed+=1
    finally:
        signal.alarm(0)
        if p.poll()is None:p.kill();p.communicate()
    for args in [[],['missing']*33]:
        r=subprocess.run([str(driver),*args],env=env,capture_output=True,timeout=20)
        assert r.returncode and b'1..32'in r.stderr and b'JIT SEQUENCE DONE'not in r.stdout;passed+=1
mode='Python-built native driver'if '--python-bootstrap'in sys.argv else 'seed-built native driver'
print(f'{passed}/{passed} sequential fresh-runtime mapping/outcome gates ({mode}; no shared state or tiering)')
