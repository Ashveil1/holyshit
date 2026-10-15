#!/usr/bin/env python3
"""x64 and candidate native seed agree on legacy/new import precedence."""
from pathlib import Path
import os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
passed=0
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp);near=d/'near';far=d/'far';near.mkdir();far.mkdir();main=near/'main.holy';main.write_text('import support\nprint support.value\n')
    env=dict(os.environ,HSPATH=str(far),HSROOT=str(ROOT))
    cases=[(None,19,99,'19\n'),(20,19,99,'19\n'),(20,None,99,'20\n'),(None,None,99,'99\n')]
    for old,new,remote,want in cases:
        for path,value in [(near/'support.hs',old),(near/'support.holy',new),(far/'support.holy',remote)]:
            path.unlink(missing_ok=True)
            if value is not None:path.write_text(f'value = {value}\n')
        for backend in ['x64','native-hs']:
            exe=d/'program'
            cmd=([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(main),str(exe)] if backend=='native-hs' else [sys.executable,str(ROOT/'hs.py'),'xbuild',str(main),'-o',str(exe)])
            r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=60)
            assert not r.returncode,(backend,r.stderr)
            r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=20)
            assert not r.returncode and r.stdout==want,(backend,r.stdout,r.stderr);passed+=1
    (near/'pkg').mkdir();(near/'pkg'/'leaf.holy').write_text('value = 37\n');main.write_text('import pkg.leaf\nprint pkg.leaf.value\n')
    for backend in ['x64','native-hs']:
        exe=d/'program';cmd=([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(main),str(exe)] if backend=='native-hs' else [sys.executable,str(ROOT/'hs.py'),'xbuild',str(main),'-o',str(exe)])
        r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=60);assert not r.returncode,(backend,r.stderr)
        r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=20)
        assert not r.returncode and r.stdout=='37\n',(backend,r.stderr);passed+=1
    main.write_text('import absent\n')
    r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(main),str(d/'bad')],env=env,capture_output=True,text=True,timeout=30)
    assert r.returncode and 'cannot find module' in r.stderr and not (d/'bad').exists(),r.stderr;passed+=1
print(f'{passed}/{passed} .holy x64/native import gates; seed audit is a separate full-CI gate')
