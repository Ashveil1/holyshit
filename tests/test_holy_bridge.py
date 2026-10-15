#!/usr/bin/env python3
"""Stage one: reference IR/interpreter, GCC and LSP dual-suffix imports."""
from pathlib import Path
import os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import interp,ir,lsp,hs
passed=0
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp);near=d/'near';far=d/'far';near.mkdir();far.mkdir();main=near/'main.holy'
    env=dict(os.environ,HSPATH=str(far),HSROOT=str(ROOT))
    for suffix in ['.hs','.holy']:
        for name in ['support.hs','support.holy']:
            (near/name).unlink(missing_ok=True)
        (near/('support'+suffix)).write_text('value = 19\n')
        main.write_text('import support\nprint support.value\n')
        expected='19\n'
        for backend in ['interp','ir','native']:
            r=subprocess.run(([sys.executable,str(ROOT/'ir.py'),str(main)] if backend=='ir' else [sys.executable,str(ROOT/'hs.py'),'run',str(main),'--backend',backend]),env=env,capture_output=True,text=True,timeout=60)
            assert r.returncode==0 and r.stdout==expected,(suffix,backend,r.stderr)
            passed+=1
    # Both in same directory: new suffix wins. Earlier directory's legacy
    # module still wins over a new-suffix file in a later directory.
    (near/'support.hs').write_text('value = 20\n');(far/'support.holy').write_text('value = 99\n')
    for expected in ['19\n','20\n']:
        for backend in ['interp','ir','native']:
            r=subprocess.run(([sys.executable,str(ROOT/'ir.py'),str(main)] if backend=='ir' else [sys.executable,str(ROOT/'hs.py'),'run',str(main),'--backend',backend]),env=env,capture_output=True,text=True,timeout=60)
            assert r.returncode==0 and r.stdout==expected,(expected,backend,r.stderr,r.stdout)
            passed+=1
        (near/'support.holy').unlink(missing_ok=True)
    old=os.environ.get('HSPATH');os.environ['HSPATH']=str(far)
    try:
        assert interp.find_module_file('support',str(near),1)==str(near/'support.hs');passed+=1
        assert ir._ir_find('support',str(near),1)==str(near/'support.hs');passed+=1
        assert lsp.find_module_file('support',str(near))==str(near/'support.hs');passed+=1
        (near/'support.hs').unlink()
        assert lsp.find_module_file('support',str(near))==str(far/'support.holy');passed+=1
    finally:
        if old is None:os.environ.pop('HSPATH',None)
        else:os.environ['HSPATH']=old
    (near/'pkg').mkdir();(near/'pkg'/'leaf.holy').write_text('value = 37\n');main.write_text('import pkg.leaf\nprint pkg.leaf.value\n')
    for backend in ['interp','ir','native']:
        r=subprocess.run(([sys.executable,str(ROOT/'ir.py'),str(main)] if backend=='ir' else [sys.executable,str(ROOT/'hs.py'),'run',str(main),'--backend',backend]),env=env,capture_output=True,text=True,timeout=60)
        assert r.returncode==0 and r.stdout=='37\n',(backend,r.stderr);passed+=1
    (near/'t_new.holy').write_text('def test_ok():\n  assert true\n');(near/'t_old.hs').write_text('def test_ok():\n  assert true\n')
    assert set(hs._test_files([str(near)]))=={str(near/'t_new.holy'),str(near/'t_old.hs')};passed+=1
    r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'test',str(near)],env=env,capture_output=True,text=True,timeout=30)
    assert r.returncode==0 and '2 passed' in r.stdout,(r.stdout,r.stderr);passed+=1
    main.write_text('print 2 + 3\n')
    r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'fmt',str(main),'--check'],env=env,capture_output=True,text=True,timeout=30)
    assert not r.returncode,r.stderr;passed+=1
print(f'{passed}/{passed} stage-one .holy reference/GCC/LSP bridge gates; native-hs bridge remains separate')
