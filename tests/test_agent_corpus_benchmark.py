#!/usr/bin/env python3
"""A19.1 preflight dict benchmark: boundedness and report contract.

Runs bench/a19_dict_benchmark.holy under the interp at TINY scale and
asserts the safety contract (design note A19 v9 section 5.2):
  - knee mode: batch rows, no-knee completion at small scale, stop
    vocabulary;
  - mem mode: RSS samples, worst-step row, completion;
  - a forced tiny budget stops the run SAFELY before the first
    insertion (STOP memory, KEYS 0) - the v9 self-budget works.
Numbers (ticks, KiB) are never asserted: only structure and stop
behavior, so the test is deterministic on any machine.
The full-scale native run is manual: python3 bench/a19_run_benchmark.py
"""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PROGRAM = ROOT / 'bench' / 'a19_dict_benchmark.holy'


def run(env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    r = subprocess.run([sys.executable, str(ROOT / 'interp.py'),
                        str(PROGRAM)], capture_output=True, text=True,
                       env=env, timeout=120)
    assert r.returncode == 0, r.stderr[-400:]
    return r.stdout.splitlines()


def field(lines, prefix):
    return [l for l in lines if l.startswith(prefix)]


def main():
    # knee mode: completes at tiny scale with a generous budget.
    lines = run({'A19_BENCH_KEYS': '2000', 'A19_BENCH_BATCH': '500',
                 'A19_BENCH_BUDGET_KB': '200000'})
    assert field(lines, 'MODE knee'), lines[0]
    b0 = field(lines, 'B0_KB ')
    assert b0 and int(b0[0].split()[1]) > 0, b0
    batches = field(lines, 'BATCH ')
    assert len(batches) == 4, batches
    for b in batches:
        p = b.split()
        assert p[2] == 'TICKS_MS' and p[4] == 'PER_INSERT_US', b
        assert int(p[3]) >= 0 and float(p[5]) >= 0, b
    assert field(lines, 'KNEE none'), lines
    stop = field(lines, 'STOP ')
    assert stop and stop[0] == 'STOP complete AT 2000', stop
    assert field(lines, 'KEYS 2000'), lines
    assert int(field(lines, 'PEAK_KB ')[0].split()[1]) > 0, lines
    print('ok knee mode: 4 batches, STOP complete AT 2000')

    # mem mode: RSS samples + worst-step row, completes.
    lines = run({'A19_BENCH_MODE': 'mem', 'A19_BENCH_KEYS': '2000',
                 'A19_BENCH_SAMPLE': '500',
                 'A19_BENCH_BUDGET_KB': '200000'})
    assert field(lines, 'MODE mem'), lines[0]
    rss = field(lines, 'RSS ')
    assert rss and rss[-1].startswith('RSS 2000 KB '), rss
    assert field(lines, 'WORST_STEP_KB '), lines
    stop = field(lines, 'STOP ')
    assert stop and stop[0] == 'STOP complete AT 2000', stop
    print('ok mem mode: RSS samples, STOP complete AT 2000')

    # forced tiny budget: stops SAFELY before the first insertion.
    lines = run({'A19_BENCH_MODE': 'mem', 'A19_BENCH_KEYS': '2000',
                 'A19_BENCH_BUDGET_KB': '1'})
    stop = field(lines, 'STOP ')
    assert stop and stop[0] == 'STOP memory AT 0', stop
    assert field(lines, 'KEYS 0'), lines
    print('ok self-budget: STOP memory AT 0, KEYS 0 (safe stop)')

    print('ok a19 dict benchmark boundedness gate')


if __name__ == '__main__':
    main()
