#!/usr/bin/env python3
"""Small cc extension bridge, including compiled-compiler fixed point."""
from pathlib import Path
import os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
passed=0
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp);source=d/'main.holy';module=d/'part.holy';old=d/'part.hs';exe=d/'program';cc=d/'cc';cc2=d/'cc2'
    env=dict(os.environ,HSPATH=str(ROOT/'selfhost'),HSROOT=str(ROOT))
    # Interpreted cc builds itself, then its own exists runtime is used when
    # that compiled compiler loads .holy imports. Same compiler bytes repeat.
    r=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(ROOT/'selfhost/cc.holy'),str(ROOT/'selfhost/cc.holy'),str(cc)],env=env,capture_output=True,text=True,timeout=90)
    assert not r.returncode,(r.stdout,r.stderr);passed+=1
    r=subprocess.run([str(cc),str(ROOT/'selfhost/cc.holy'),str(cc2)],env=env,capture_output=True,text=True,timeout=90)
    assert not r.returncode and cc.read_bytes()==cc2.read_bytes(),(r.stdout,r.stderr);passed+=1
    for new,legacy,want in [(19,20,'19\n'),(19,None,'19\n'),(None,20,'20\n')]:
        for path,value in [(module,new),(old,legacy)]:
            path.unlink(missing_ok=True)
            if value is not None:path.write_text(f'value = {value}\n')
        source.write_text('import part\nprint part.value\n')
        reference=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,text=True,timeout=20)
        # On pre-reference bridge base, only legacy ref is resolvable; pin
        # expected independently here, then final integration adds parity.
        for command in [[sys.executable,str(ROOT/'interp.py'),str(ROOT/'selfhost/cc.holy')],[str(cc)]]:
            r=subprocess.run(command+[str(source),str(exe)],env=env,capture_output=True,text=True,timeout=60)
            assert not r.returncode,(r.stdout,r.stderr)
            r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=20)
            assert not r.returncode and r.stdout==want,(r.stdout,r.stderr);passed+=1
    # exists is the dependency needed by the compiled compiler's resolver.
    source.write_text('print exists('+repr(str(ROOT/'README.md'))+')\nprint exists('+repr(str(d/'missing'))+')\n')
    # hs uses double quoted string literals only.
    source.write_text(source.read_text().replace("'",'"'))
    ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,text=True,timeout=20)
    r=subprocess.run([str(cc),str(source),str(exe)],env=env,capture_output=True,text=True,timeout=30);assert not r.returncode,(r.stdout,r.stderr)
    r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=20)
    assert (r.returncode,r.stdout,r.stderr)==(ref.returncode,ref.stdout,ref.stderr),(r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} small-cc .holy bridge and native self-repeat gates')
