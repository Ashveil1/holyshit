#!/usr/bin/env python3
"""Moved native bundle operates with no checkout reference or Python/gcc PATH."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
passed=failed=0
def check(ok,label):
    global passed,failed
    passed+=int(ok);failed+=int(not ok)
    if not ok:print('FAIL',label,flush=True)
with tempfile.TemporaryDirectory(prefix='hs bundle space ') as temp:
    d=Path(temp);bindir=d/'utilities';bindir.mkdir()
    for name in ['dirname','sha256sum','mktemp','rm','mkdir','cp','chmod','mv','cmp']:
        (bindir/name).symlink_to(shutil.which(name))
    env=dict(os.environ,PATH=str(bindir));env.pop('HSPATH',None);env.pop('HSROOT',None)
    original=d/'original';moved=d/'moved bundle'
    r=subprocess.run(['/bin/sh',str(ROOT/'scripts/build-native-bundle.sh'),str(original)],env=env,capture_output=True,text=True,timeout=240)
    check(r.returncode==0,'build '+r.stderr[-150:])
    if r.returncode:sys.exit(1)
    original.rename(moved)
    launcher=moved/'bin/hs';compiler=moved/'bootstrap/hs-hosted-x86_64'
    source=d/'main file.hs';module=d/'support.hs';module.write_text('value = 19\n')
    source.write_text('import support\nprint support.value\nprint json_str([1, "ok"])\nprint argv()\nextern:\n  I64 printf(Str format, ..., I64 n)\nprintf("value=%lld\\n", 27)\n')
    expected='19\n[1, "ok"]\n[hello world, $5]\nvalue=27\n'
    # Keep PATH isolated and all sources outside both bundle and checkout.
    r=subprocess.run(['/bin/sh',str(launcher),'run',source.name,'hello world','$5'],cwd=d,env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==0 and r.stdout==expected,'relocated eager JSON/import/argv/variadic '+repr((r.returncode,r.stdout,r.stderr[-150:])))
    exe=d/'program'
    r=subprocess.run(['/bin/sh',str(launcher),'build',source.name,str(exe)],cwd=d,env=env,capture_output=True,text=True,timeout=60)
    if r.returncode==0:r=subprocess.run([str(exe),'hello world','$5'],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode==0 and r.stdout==expected,'relocated AOT '+repr((r.returncode,r.stdout,r.stderr[-150:])))
    local=dict(env,HSROOT=str(moved),HSPATH=str(moved/'selfhost')+':'+str(moved/'selfhost/be'))
    stage=d/'stage2'
    if '--skip-selfcompile' not in sys.argv:
        r=subprocess.run([str(compiler),str(moved/'selfhost/be/compile.hs'),str(stage)],env=local,capture_output=True,text=True,timeout=180)
        check(r.returncode==0 and stage.read_bytes()==compiler.read_bytes(),'relocated compiler self-compilation')
    source.write_text('print 1 / 0\n')
    r=subprocess.run(['/bin/sh',str(launcher),'run',str(source)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode!=0 and 'division by zero' in r.stderr,'runtime error status')
    source.write_text('if\n');exe.write_bytes(b'preserve')
    r=subprocess.run(['/bin/sh',str(launcher),'build',str(source),str(exe)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode!=0 and exe.read_bytes()==b'preserve','invalid source preserves output')
    source.write_text('print "TARGET RAN"\n')
    eager=moved/'bin/hs-eager';data=eager.read_bytes();eager.write_bytes(data+b'changed')
    r=subprocess.run(['/bin/sh',str(launcher),'run',str(source)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode!=0 and 'TARGET RAN' not in r.stdout,'corrupt eager binary refused before execution')
    eager.write_bytes(data)
    before=(moved/'EAGER_SHA256SUMS').read_bytes()
    r=subprocess.run(['/bin/sh',str(ROOT/'scripts/build-native-bundle.sh'),str(moved)],env=env,capture_output=True,text=True,timeout=30)
    check(r.returncode!=0 and (moved/'EAGER_SHA256SUMS').read_bytes()==before,'existing directory refused')
print(f'{passed}/{passed+failed} relocated native bundle gates (PATH without Python/gcc)')
sys.exit(bool(failed))
