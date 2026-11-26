#!/usr/bin/env python3
"""A19.1 preflight dict benchmark runner (design note A19 v9 section 5.2).

Builds bench/a19_dict_benchmark.holy natively (unless --exe is given)
and runs it in THREE throwaway processes, each exiting before the next
starts, so benchmark memory never coexists across measurements:

  1. MODE=knee  - performance knee (ticks), full key count.
  2. MODE=mem   - bytes-per-entry (VmHWM), full key count, with the
     v9 self-budget enforced before every insertion.
  3. MODE=mem at the derived ceiling K - the measured dict peak RSS at
     the exact pilot ceiling count; this is the pilot's dict admission
     bound ("the largest benchmarked key count, or the ceiling if
     lower").

Every process's peak RSS is ALSO recorded externally via
resource.ru_maxrss as a cross-check of the in-hs VmHWM samples.

Outputs <out>.json (machine) and <out>.txt (human report). The report
carries the A19 honesty wording: these are measurements of the runtime
dict with production-shaped records, nothing else.

    python3 bench/a19_run_benchmark.py [--keys 200000] [--exe PATH]
                                       [--out bench/a19-benchmark]
                                       [--no-build]
"""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PROGRAM = ROOT / 'bench' / 'a19_dict_benchmark.holy'

FIXED_SAMPLE_KEYS = (10000, 50000, 100000, 200000)


def build_exe(tmp):
    image = Path(tmp) / 'a19-dict-benchmark'
    env = dict(os.environ)
    env['HSPATH'] = str(ROOT)
    r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build',
                        str(PROGRAM), '-o', str(image)],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0 or not image.exists():
        raise SystemExit('native benchmark build failed: ' + r.stderr[-400:])
    return str(image)


def run_mode(exe, mode, keys, extra_env=None):
    env = dict(os.environ)
    env['A19_BENCH_MODE'] = mode
    env['A19_BENCH_KEYS'] = str(keys)
    if extra_env:
        env.update(extra_env)
    # A wrapper process per run: its RUSAGE_CHILDREN is scoped to this
    # child only, giving a per-run external maxrss cross-check.
    wrap = ('import resource,subprocess,sys;'
            'r=subprocess.run(sys.argv[1:]);'
            'print("MAXRSS_KB", resource.getrusage('
            'resource.RUSAGE_CHILDREN).ru_maxrss);'
            'sys.exit(r.returncode)')
    r = subprocess.run([sys.executable, '-c', wrap, exe],
                       capture_output=True, text=True, env=env, timeout=1800)
    if r.returncode != 0:
        raise SystemExit(f'benchmark mode={mode} failed rc={r.returncode}: '
                         + r.stderr[-400:])
    ext = -1
    body = []
    for line in r.stdout.splitlines():
        if line.startswith('MAXRSS_KB '):
            ext = int(line.split()[1])
        else:
            body.append(line)
    out = {'mode': mode, 'planned_keys': keys, 'stdout': '\n'.join(body),
           'external_maxrss_kb': ext,
           'batches': [], 'rss_samples': {}}
    r = type('R', (), {'stdout': '\n'.join(body)})
    for line in r.stdout.splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == 'BATCH':
            out['batches'].append({'keys': int(p[1]),
                                   'ticks_ms': int(p[3]),
                                   'per_insert_us': float(p[5])})
        elif p[0] == 'RSS':
            out['rss_samples'][int(p[1])] = int(p[3])
        elif p[0] == 'B0_KB':
            out['b0_kb'] = int(p[1])
        elif p[0] == 'BUDGET_KB':
            out['budget_kb'] = int(p[1])
        elif p[0] == 'KNEE':
            out['knee'] = None if p[1] == 'none' else int(p[1])
        elif p[0] == 'WORST_STEP_KB':
            out['worst_step_kb'] = int(p[1])
            out['worst_step_at'] = int(p[3])
        elif p[0] == 'STOP':
            out['stop_reason'] = p[1]
            out['stop_at'] = int(p[3])
        elif p[0] == 'PEAK_KB':
            out['peak_kb'] = int(p[1])
        elif p[0] == 'KEYS':
            out['keys'] = int(p[1])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keys', type=int, default=200000)
    ap.add_argument('--exe')
    ap.add_argument('--out', default=str(ROOT / 'bench' / 'a19-benchmark'))
    ap.add_argument('--no-build', action='store_true')
    args = ap.parse_args()

    import tempfile
    if args.exe:
        exe = args.exe
    else:
        tmp = tempfile.mkdtemp(prefix='a19-bench-build-')
        exe = build_exe(tmp)
    exe_sha = __import__('hashlib').sha256(Path(exe).read_bytes()).hexdigest()

    knee = run_mode(exe, 'knee', args.keys)
    mem = run_mode(exe, 'mem', args.keys)

    if knee.get('knee'):
        ceiling = min(50000, knee['knee'] // 2)
    else:
        ceiling = 50000
    # The ceiling run measures the dict at the exact pilot ceiling count.
    # Its budget is a MEASUREMENT ENVELOPE derived from the mem run's worst
    # observed per-entry cost (the pinned 1 KiB/entry was refuted by the
    # full mem run when this note appears), never the pinned constant;
    # the admission bound is the run's MEASURED peak, not the envelope.
    per_entry_worst = 0.0
    for k, kb in mem['rss_samples'].items():
        if mem.get('b0_kb', 0) > 0:
            per_entry_worst = max(per_entry_worst,
                                  (kb - mem['b0_kb']) / k)
    envelope_kb = int((ceil_b0_estimate := 3000) + ceiling
                      * max(per_entry_worst, 1.0) * 2.0) + 1024
    ceil = run_mode(exe, 'mem', ceiling,
                    {'A19_BENCH_BUDGET_KB': str(envelope_kb)})
    ceil['budget_basis'] = (f'measurement envelope: 2x worst measured '
                            f'per-entry ({per_entry_worst:.3f} KiB); the '
                            f'admission bound is the measured peak, not '
                            f'this envelope')

    report = {
        'benchmark': 'a19-preflight-dict',
        'design': 'A19 v9 section 5.2',
        'exe_sha256': exe_sha,
        'planned_keys': args.keys,
        'knee_run': knee,
        'mem_run': mem,
        'ceiling_run': ceil,
        'derived': {
            'knee_keys': knee.get('knee'),
            'unique_key_ceiling': ceiling,
            'ceiling_basis': ('min(50000, knee/2)' if knee.get('knee')
                              else 'no knee found; pinned 50000'),
            'dict_admission_bound_kb': ceil.get('peak_kb'),
            'dict_admission_bound_basis': (
                f'measured peak RSS at the ceiling count {ceiling}'),
        },
    }
    # Per-entry bytes at the fixed samples that were reached.
    per_entry = {}
    for k in FIXED_SAMPLE_KEYS + (mem.get('stop_at') or 0,):
        if k and k in mem['rss_samples'] and mem.get('b0_kb', 0) > 0:
            per_entry[k] = round((mem['rss_samples'][k] - mem['b0_kb'])
                                 / k, 3)
    report['derived']['bytes_per_entry_kib_by_count'] = per_entry
    report['derived']['pinned_bound_kib'] = 1.0
    report['derived']['pinned_bound_holds'] = all(
        v <= 1.0 for v in per_entry.values())

    out_json = Path(args.out).with_suffix('.json')
    out_txt = Path(args.out).with_suffix('.txt')
    out_json.write_text(json.dumps(report, indent=1) + '\n')

    lines = []
    a = lines.append
    a('A19.1 preflight dict benchmark report (design note A19 v9 section 5.2)')
    a('Measures the runtime dict with production-shaped records (128 B keys,')
    a('512 B values, all distinct). UNVERIFIED measurements of THIS build on')
    a('THIS machine; not a quality claim about anything else.')
    a('')
    a(f'executable sha256: {exe_sha}')
    a(f'planned keys: {args.keys}')
    a('')
    a(f'KNEE RUN: B0 {knee.get("b0_kb")} KiB; stop: {knee.get("stop_reason")} '
      f'at {knee.get("stop_at")}; knee: {knee.get("knee")}; '
      f'peak {knee.get("peak_kb")} KiB '
      f'(external maxrss {knee.get("external_maxrss_kb")} KiB)')
    a(f'MEM RUN: B0 {mem.get("b0_kb")} KiB; budget {mem.get("budget_kb")} KiB; '
      f'stop: {mem.get("stop_reason")} at {mem.get("stop_at")}; '
      f'peak {mem.get("peak_kb")} KiB '
      f'(external maxrss {mem.get("external_maxrss_kb")} KiB)')
    for k in FIXED_SAMPLE_KEYS:
        if k in mem['rss_samples']:
            a(f'  RSS at {k} keys: {mem["rss_samples"][k]} KiB '
              f'({per_entry.get(k)} KiB/entry over B0)')
    a(f'  worst per-sample step: {mem.get("worst_step_kb")} KiB '
      f'at {mem.get("worst_step_at")} keys')
    a('')
    a(f'DERIVED unique-key ceiling K = {ceiling} '
      f'({report["derived"]["ceiling_basis"]})')
    a(f'CEILING RUN at K: stop: {ceil.get("stop_reason")} at '
      f'{ceil.get("stop_at")}; peak {ceil.get("peak_kb")} KiB '
      f'(external maxrss {ceil.get("external_maxrss_kb")} KiB)')
    a(f'DICT ADMISSION BOUND for the pilot: {ceil.get("peak_kb")} KiB '
      f'(measured peak RSS at the ceiling count, never an interpolated slope)')
    if not report['derived']['pinned_bound_holds']:
        a('NOTE: the pinned 1 KiB/entry conservative bound did NOT hold at '
          'the measured counts; the measured values REPLACE it (design 5.3: '
          'the dry run/benchmark measurement replaces the pinned constant).')
    out_txt.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print('wrote', out_json, 'and', out_txt)


if __name__ == '__main__':
    main()
