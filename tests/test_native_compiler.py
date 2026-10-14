#!/usr/bin/env python3
"""Compiled hs source compiler emits Python-identical ELF images.
Unsafe words through 64 bits are decoded without tagged-Int truncation.
"""
import contextlib
import glob
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import interp
import ir
import irx64
from x64gen import build_x64
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
passed=failed=rejected=0
with tempfile.TemporaryDirectory() as d:
    exe=str(Path(d)/'hs-compiler')
    old=os.environ.get('HSPATH')
    os.environ['HSPATH']=env['HSPATH']
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc=build_x64(str(ROOT/'selfhost/be/compile_hex.hs'),exe)
    finally:
        if old is None:os.environ.pop('HSPATH',None)
        else:os.environ['HSPATH']=old
    if rc:raise SystemExit('FAIL native compiler build')
    for f in sorted(glob.glob(str(ROOT/'tests/*.hs'))):
        if sys.argv[1:] and Path(f).name not in sys.argv[1:]:continue
        try:
            interp.reset_parse_state()
            module=ir.build_module(interp.parse_program(Path(f).read_text()))
            want=irx64.GenIR(module,str(Path(f).parent)).build_ir_image().hex()
        except Exception:
            rejected+=1
            continue
        r=subprocess.run([exe,f],env=env,capture_output=True,text=True,errors='replace',timeout=120)
        ok="".join(r.stdout.split())==want
        passed+=int(ok);failed+=int(not ok)
        if not ok:print('FAIL native compiler',Path(f).name,r.stderr[-180:],flush=True)
    # Boundary unsafe literals, including decimal, uppercase hex and unary minus.
    words = [2**61-1, 2**61, 2**63-1, 2**63, 2**64-1]
    for word in words:
        for literal in [str(word), hex(word), "0X"+format(word,"X"), "-"+hex(word)]:
            source_text = "unsafe:\n  U64 v = "+literal+"\n  print v\n"
            f = str(Path(d)/"word.hs")
            Path(f).write_text(source_text)
            interp.reset_parse_state()
            want = irx64.GenIR(ir.build_module(interp.parse_program(source_text)),d).build_ir_image().hex()
            r = subprocess.run([exe,f],env=env,capture_output=True,text=True,timeout=120)
            ok = r.returncode == 0 and "".join(r.stdout.split()) == want
            passed += int(ok); failed += int(not ok)
            if not ok: print("FAIL unsafe literal",literal,r.stderr[-180:])
    # Native compiler builds itself, then the resulting compiler repeats it.
    source = str(ROOT/'selfhost/be/compile_hex.hs')
    previous = Path(exe).read_bytes()
    for generation in [2, 3]:
        outpath = Path(d)/f'stage{generation}.hex'
        errpath = Path(d)/f'stage{generation}.err'
        with outpath.open('w') as out, errpath.open('w') as err:
            result = subprocess.run([exe, source], stdout=out, stderr=err,
                env=env, timeout=600)
        try:
            image = bytes.fromhex(''.join(outpath.read_text().split()))
            ok = result.returncode == 0 and image == previous
        except Exception:
            ok = False
        passed += int(ok)
        failed += int(not ok)
        if not ok:
            print('FAIL fixed point stage',generation,errpath.read_text()[-200:])
            break
        exe = str(Path(d)/f'stage{generation}')
        Path(exe).write_bytes(image)
        Path(exe).chmod(0o755)
        previous = image
    # Binary-output driver can write and run a program without hex decoding.
    binary_exe = str(Path(d)/'hs-binary')
    os.environ['HSPATH'] = env['HSPATH']
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = build_x64(str(ROOT/'selfhost/be/compile.hs'), binary_exe)
    finally:
        if old is None:os.environ.pop('HSPATH',None)
        else:os.environ['HSPATH']=old
    target = str(Path(d)/'fib')
    result = subprocess.run([binary_exe,str(ROOT/'tests/fib.hs'),target],env=env,
        capture_output=True,text=True,timeout=120) if not rc else None
    ok = result is not None and result.returncode == 0 and Path(target).exists()
    if ok:
        interp.reset_parse_state()
        expected = irx64.GenIR(ir.build_module(interp.parse_program((ROOT/'tests/fib.hs').read_text())),str(ROOT/'tests')).build_ir_image()
        ok = Path(target).read_bytes() == expected
    passed += int(ok)
    failed += int(not ok)
    if not ok:print('FAIL native binary-output compiler')
print(f'{passed}/{passed+failed} passed ({rejected} rejected by Python emitter)')
sys.exit(bool(failed) or not passed)
