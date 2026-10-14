#!/usr/bin/env python3
"""Compare already-built eager JIT driver (compile+run) against prebuilt AOT.
No Python semantic/compiler process runs inside the timed JIT path.
Usage: python3 bench/jit.py /path/to/hs-jit [--runs 5] [--timeout 60]
Driver setup is excluded. Every timed run checks status and exact stdout.
"""
from pathlib import Path
import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('driver',type=Path)
p.add_argument('--runs',type=int,default=5)
p.add_argument('--timeout',type=float,default=60)
a=p.parse_args()
if a.runs<1 or a.timeout<=0:p.error('runs and timeout must be positive')
driver=a.driver.resolve()
if not driver.is_file():p.error('driver does not exist')
env=dict(os.environ,HSROOT=str(ROOT),HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'))
with tempfile.TemporaryDirectory() as d:
    for name in ['fib','loop','dict','alloc','strings']:
        source=ROOT/'bench'/f'{name}.hs';exe=str(Path(d)/name)
        # Untimed setup uses the audited native hs compiler, not Python.
        subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),exe],env=env,check=True,timeout=a.timeout,capture_output=True)
        samples={'aot':[],'jit':[]};expected=None
        for i in range(a.runs):
            commands=[('aot',[exe]),('jit',[str(driver),str(source)])]
            for kind,command in commands[::1 if i%2==0 else -1]:
                started=time.perf_counter()
                r=subprocess.run(command,env=env,capture_output=True,timeout=a.timeout)
                elapsed=time.perf_counter()-started
                if r.returncode:raise SystemExit(f'{name}/{kind} failed: {r.returncode}: '+r.stderr.decode(errors='replace')[-200:])
                if expected is None:expected=r.stdout
                if r.stdout!=expected:raise SystemExit(f'{name}/{kind}: output mismatch')
                samples[kind].append(elapsed)
        med={k:statistics.median(v) for k,v in samples.items()}
        print(json.dumps({'case':name,'runs':a.runs,'seconds':med,'jit_over_aot':med['jit']/med['aot'],'scope':'JIT includes compilation; AOT excludes compilation; driver build excluded','output':'same'}),flush=True)
