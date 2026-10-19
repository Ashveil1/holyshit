#!/usr/bin/env python3
"""Phase-5 cache gate: the JIT driver's .hsc compiled-code cache.

The driver snapshots the assembler state after codegen next to the source
(<prog>.hsc), keyed on the bytes of the program and every module it pulled
in. A hit skips parse/IR/codegen: same output, warm run fast. Correctness
fixtures prove the fallbacks - source edit, module edit, cache corruption,
unwritable directory - all recompile cleanly, and that per-run argv/env
never leak through the cache. Timed fixtures gate warm startup: json_* warm
under 50ms (it was ~270ms cold via runtime/json.holy) and bench warm runs
within 1.10x of the equivalent AOT binary (bench/jit.py).
"""
from pathlib import Path
import json,os,statistics,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
passed=failed=0
def check(ok,label):
    global passed,failed
    passed+=int(ok);failed+=int(not ok)
    if not ok:print('FAIL',label,flush=True)
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
def run(driver,source,args=(),extra_env=None,timeout=60):
    e=dict(env)
    if extra_env:e.update(extra_env)
    return subprocess.run([str(driver),str(source),*args],env=e,capture_output=True,timeout=timeout)
def timed(driver,source,n=7):
    run(driver,source)
    ts=[]
    for _ in range(n):
        t0=time.perf_counter()
        r=run(driver,source)
        ts.append((time.perf_counter()-t0)*1000)
        assert r.returncode==0,(source,r.stderr[-200:])
    return statistics.median(ts)
with tempfile.TemporaryDirectory() as d:
    d=Path(d)
    exe=d/'jit'
    r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/jit_run.holy'),str(exe)],env=env,capture_output=True,text=True,timeout=240)
    check(r.returncode==0,'native JIT driver build '+r.stderr[-200:])
    if r.returncode:sys.exit(1)
    # 1. Cold run writes the cache; warm run is byte-identical.
    hello=d/'hello.holy';hello.write_text('print "hello"\n')
    r1=run(exe,hello);r2=run(exe,hello)
    check(r1.returncode==0 and r1.stdout==b'hello\n','cache cold run')
    check(r2.returncode==0 and r2.stdout==r1.stdout,'cache warm identical')
    check((d/'hello.hsc').is_file(),'cache file written')
    # 2. Editing the source invalidates.
    hello.write_text('print "bye"\n')
    r=run(exe,hello)
    check(r.returncode==0 and r.stdout==b'bye\n','source edit invalidates')
    # 3. Editing an imported module invalidates.
    (d/'helper.holy').write_text('def value():\n  return 1\n')
    prog=d/'prog.holy';prog.write_text('import helper\nprint helper.value()\n')
    r=run(exe,prog)
    check(r.returncode==0 and r.stdout==b'1\n','module program cold')
    (d/'helper.holy').write_text('def value():\n  return 2\n')
    r=run(exe,prog)
    check(r.returncode==0 and r.stdout==b'2\n','module edit invalidates')
    # 4. A corrupted cache falls back to a correct recompile.
    (d/'hello.hsc').write_bytes(b'HSC1 garbage not a real cache')
    r=run(exe,hello)
    check(r.returncode==0 and r.stdout==b'bye\n','corrupt cache falls back')
    r=run(exe,hello)
    check(r.returncode==0 and r.stdout==b'bye\n','corrupt cache regenerated')
    # 5. The environment is re-baked per run, never cached.
    av=d/'args.holy';av.write_text('print env("HS_CACHE_PROBE")\n')
    r1=run(exe,av,extra_env={'HS_CACHE_PROBE':'A'})
    r2=run(exe,av,extra_env={'HS_CACHE_PROBE':'B'})
    check(r1.stdout==b'A\n' and r2.stdout==b'B\n','env fresh per run')
    # 6. An unwritable directory still runs (cache write skipped silently).
    ro=d/'ro';ro.mkdir()
    rp=ro/'x.holy';rp.write_text('print "ro"\n')
    ro.chmod(0o555)
    r=run(exe,rp)
    check(r.returncode==0 and r.stdout==b'ro\n','unwritable dir runs')
    ro.chmod(0o755)
    # 7. A program that fails to compile leaves no cache behind.
    bad=d/'bad.holy';bad.write_text('print (\n')
    r=run(exe,bad)
    check(r.returncode==1 and not (d/'bad.hsc').exists(),'failed compile writes no cache')
    # 8. json_* warm startup joins the timed gate under 50ms.
    js=d/'json.holy';js.write_text('print json_str([1, "ok", [2, 3]])\n')
    r=run(exe,js)
    check(r.returncode==0 and r.stdout==b'[1, "ok", [2, 3]]\n','json correct')
    med=timed(exe,js)
    check(med<50,f'json warm median {med:.1f}ms < 50ms')
    # 9. Warm JIT within 1.10x of AOT on the five bench cases.
    r=subprocess.run([sys.executable,str(ROOT/'bench/jit.py'),str(exe),'--runs','7'],env=env,capture_output=True,text=True,timeout=600)
    check(r.returncode==0,'bench/jit.py '+r.stderr[-300:])
    for line in r.stdout.splitlines():
        row=json.loads(line)
        check(row['jit_over_aot']<=1.10,f"bench {row['case']} warm ratio {row['jit_over_aot']:.3f} <= 1.10")
print(f'{passed} passed, {failed} failed')
sys.exit(1 if failed else 0)
