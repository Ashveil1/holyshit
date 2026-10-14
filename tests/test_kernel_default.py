#!/usr/bin/env python3
"""Public xkernel selects IR; AST remains explicit, not a silent fallback."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from x64gen import build_xkernel
os.environ['HSPATH']=str(ROOT)+os.pathsep+os.environ.get('HSPATH','')
with tempfile.TemporaryDirectory() as d:
    d=Path(d);src=str(ROOT/'kernel/kx2.hs')
    with contextlib.redirect_stdout(io.StringIO()):
        assert build_xkernel(src,str(d/'default'))==0
        assert build_xkernel(src,str(d/'ir'),ir_backend=True)==0
        assert build_xkernel(src,str(d/'ast'),ir_backend=False)==0
    r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',src,'-o',str(d/'cli')],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert (d/'default').read_bytes()==(d/'ir').read_bytes()==(d/'cli').read_bytes()
    assert (d/'ast').read_bytes()!=(d/'ir').read_bytes()
print('1/1 public kernel IR selection gate')
