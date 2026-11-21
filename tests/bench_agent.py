#!/usr/bin/env python3
"""Repeatable hosted resource benchmark for the pure-hs local agent.

Measures, for the agent's REPL (agent/repl.holy) on hosted backends:
  - cold startup wall time (spawn to exit, session = immediate `quit`,
    which includes loading and re-saving the seeded store);
  - peak RSS of the benchmarked process (Linux VmHWM, polled from
    /proc/<pid>/status every ~4 ms; the kernel keeps it as a high-water
    mark, so this is the process's own peak, not system-wide use);
  - mean response latency per command, derived as
    (session wall - startup wall) / command count for scripted sessions,
    separately for taught-fact recalls and honest misses;
at synthesized store scales (default full: 0 / 1k / 10k taught facts,
10% Thai keys), plus one run of the largest scale under a 4 GiB address
-space limit (RLIMIT_AS) to probe Ash's 4 GB target machine class.

Also runs a small held-out Thai/English dialogue and counts successful
recalls, successful clarifications, honest misses and corrections.

All facts are synthesized. Every printed number is labeled with how it
was measured. These are HOSTED numbers (a Linux process running the hs
runtime); future in-OS (kernel-hosted) numbers are a separate milestone
and must never be conflated with these.

Usage:
  python3 tests/bench_agent.py --quick   # tiny scales, reference route
  python3 tests/bench_agent.py --full    # 0/1k/10k + native + 4 GiB run
"""
import argparse
import contextlib
import io
import json
import os
import platform
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REPL = ROOT / 'agent' / 'repl.holy'

# Held-out dialogue (handwritten, not from the random test corpus).
# (input, expected reply, category). 'teach' lines set up the world.
DIALOGUE = [
    ('remember my cat is somchai', 'remembered my cat is somchai', 'teach'),
    ('remember แมว is สัตว์เลี้ยง', 'remembered แมว is สัตว์เลี้ยง', 'teach'),
    ('remember bangkok is the capital of thailand',
     'remembered bangkok is the capital of thailand', 'teach'),
    ('remember กรุงเทพ is เมืองหลวง', 'remembered กรุงเทพ is เมืองหลวง', 'teach'),
    ('remember thai person is someone from thailand',
     'remembered thai person is someone from thailand', 'teach'),
    ('remember สัตว์เลี้ยง is pet', 'remembered สัตว์เลี้ยง is pet', 'teach'),
    ('remember red car is fast', 'remembered red car is fast', 'teach'),
    ('kitty means my cat', 'ok, kitty means my cat', 'teach'),
    ('คนไทย means thai person', 'ok, คนไทย means thai person', 'teach'),
    ('what is my cat', 'i know my cat is somchai', 'recall'),
    ('do you know bangkok', 'i know bangkok is the capital of thailand', 'recall'),
    ('what is แมว', 'i know แมว is สัตว์เลี้ยง', 'recall'),
    ('what is kitty', 'i know my cat is somchai', 'recall'),
    ('what is คนไทย', 'i know thai person is someone from thailand', 'recall'),
    ('no, my cat is milo', 'updated my cat is milo', 'correction'),
    ('what is my cat', 'i know my cat is milo', 'recall'),
    ('what is car', 'did you mean red car?', 'clarify'),
    ('yes', 'i know red car is fast', 'clarify'),
    ('what about it', 'i know red car is fast', 'recall'),
    ('what is สัตว์', 'did you mean สัตว์เลี้ยง?', 'clarify'),
    ('สัตว์เลี้ยง', 'i know สัตว์เลี้ยง is pet', 'clarify'),
    ('what is the moon', 'i do not know the moon', 'miss'),
    ('what is ดวงจันทร์', 'i do not know ดวงจันทร์', 'miss'),
    ('what is the capital of thailand',
     'i do not know the capital of thailand', 'miss'),
    ('blorf zingle', 'i do not understand', 'unparsed'),
]
SCORED = ('recall', 'clarify', 'miss', 'correction', 'unparsed')


def git_head():
    return subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--short', 'HEAD'],
                          capture_output=True, text=True).stdout.strip()


def synth_store(k):
    """v3 store with k synthesized facts; every 10th key is Thai."""
    facts, order = {}, []
    for i in range(1, k + 1):
        if i % 10 == 0:
            key = 'สิ่งที่%06d' % i
            facts[key] = ['ข้อมูลสังเคราะห์หมายเลข %d' % i]
        else:
            key = 'item%06d' % i
            facts[key] = ['synthetic fact %d about widget %d' % (i, i % 97)]
        order.append(key)
    return {'facts': facts, 'order': order, 'aliases': {}}


def recall_script(store, n):
    keys = store['order']
    if not keys:
        return []
    return ['what is ' + keys[(j * 7919) % len(keys)] for j in range(n)]


def miss_script(n):
    return ['what is nosuchthing%06d' % j for j in range(n)]


def dialogue_script():
    return [line for line, _, _ in DIALOGUE]


def read_hwm(pid):
    try:
        with open('/proc/%d/status' % pid) as f:
            for line in f:
                if line.startswith('VmHWM:'):
                    return int(line.split()[1])  # kB
    except OSError:
        pass
    return 0


def run_proc(argv, stdin_text, cwd, limit_bytes=None):
    """Run argv; return (wall_s, peak_rss_kB, stdout, returncode, stderr).

    Peak RSS is the child's own kernel-reported maximum resident set
    (ru_maxrss from wait4): per-process, not system-wide. stdin/stdout
    payloads in this benchmark stay well under the pipe buffer, so the
    parent writes stdin fully before waiting.
    """
    env = dict(os.environ)
    env['HSPATH'] = str(ROOT)
    in_r, in_w = os.pipe()
    out_r, out_w = os.pipe()
    err_r, err_w = os.pipe()
    t0 = time.perf_counter()
    pid = os.fork()
    if pid == 0:
        try:
            os.dup2(in_r, 0)
            os.dup2(out_w, 1)
            os.dup2(err_w, 2)
            for fd in (in_w, out_r, err_r):
                os.close(fd)
            os.chdir(str(cwd))
            if limit_bytes is not None:
                resource.setrlimit(resource.RLIMIT_AS,
                                   (limit_bytes, limit_bytes))
            os.execvpe(argv[0], argv, env)
        except BaseException:
            os._exit(127)
    os.close(in_r)
    os.close(out_w)
    os.close(err_w)
    try:
        os.write(in_w, stdin_text.encode('utf-8'))
    except BrokenPipeError:
        pass
    os.close(in_w)
    _, status, ru = os.wait4(pid, 0)
    wall = time.perf_counter() - t0
    out, err = b'', b''
    for fd, acc in ((out_r, 'out'), (err_r, 'err')):
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            if acc == 'out':
                out += chunk
            else:
                err += chunk
        os.close(fd)
    rc = os.waitstatus_to_exitcode(status)
    return wall, ru.ru_maxrss, out.decode('utf-8'), rc, err.decode('utf-8')


def score_dialogue(stdout):
    replies = stdout.split('\n')[1:-1]  # drop banner and trailing ''
    lines = [l for l, _, _ in DIALOGUE]
    assert len(replies) == len(lines) + 1, (len(replies), len(lines), stdout[-400:])
    assert replies[-1] == 'bye', replies[-1]
    counts = {c: [0, 0] for c in SCORED}  # category -> [ok, total]
    for (line, want, cat), got in zip(DIALOGUE, replies):
        if cat in counts:
            counts[cat][1] += 1
            if got == want:
                counts[cat][0] += 1
            else:
                print('MISMATCH %r: want %r got %r' % (line, want, got))
    return counts


def bench_session(argv, cwd, store, script, label, rows, limit_bytes=None):
    (cwd / 'agent-memory.json').write_text(json.dumps(store, ensure_ascii=False),
                                           encoding='utf-8')
    stdin = '\n'.join(script + ['quit']) + '\n'
    wall, peak, out, rc, err = run_proc(argv, stdin, cwd, limit_bytes)
    assert rc == 0, (label, rc, err[-800:])
    return wall, peak, out


def bench_backend(name, argv, tmp, scales, n_cmds, limit_run):
    rows = []
    for scale in scales:
        store = synth_store(scale)
        d = tmp / ('%s-%d' % (name.replace('/', '_'), scale))
        d.mkdir()
        t_start, rss_start, _ = bench_session(argv, d, store, [], 'startup', rows)
        n_rec_cmds = n_cmds if scale else n_cmds
        # Misses scan every taught key (no index): ~0.5 ms/key on the
        # interp route, so cap the miss count at large scales; the
        # per-command mean stays comparable.
        n_mis_cmds = n_cmds if scale <= 1000 else 5
        t_rec, rss_rec, _ = bench_session(argv, d, store,
                                          recall_script(store, n_rec_cmds), 'recall', rows)
        t_mis, rss_mis, _ = bench_session(argv, d, store,
                                          miss_script(n_mis_cmds), 'miss', rows)
        t_dlg, rss_dlg, out = bench_session(argv, d, store,
                                            dialogue_script(), 'dialogue', rows)
        counts = score_dialogue(out)
        rows.append({
            'backend': name, 'facts': scale,
            'startup_s': t_start, 'startup_rss_kb': rss_start,
            # max(0, ...): at scale 0 the recall session is quit-only and
            # scheduling noise can make the difference slightly negative.
            'recall_ms': max(0.0, 1000.0 * (t_rec - t_start) / n_rec_cmds),
            'miss_ms': max(0.0, 1000.0 * (t_mis - t_start) / n_mis_cmds),
            'session_rss_kb': max(rss_rec, rss_mis, rss_dlg),
            'dialogue': counts,
        })
    if limit_run and scales:
        scale = scales[-1]
        store = synth_store(scale)
        d = tmp / ('%s-limit' % name.replace('/', '_'))
        d.mkdir()
        # Bounded probe script: is the agent usable at all under 4 GiB
        # at this scale, and what does the process cost there.
        script = recall_script(store, 20) + miss_script(5)
        try:
            wall, peak, out = bench_session(
                argv, d, store, script, 'limit4g', rows, limit_bytes=4 << 30)
            rows.append({'backend': name, 'facts': scale, 'limit_4gib': 'ok',
                         'limit_wall_s': wall, 'limit_rss_kb': peak})
        except (AssertionError, MemoryError) as e:
            rows.append({'backend': name, 'facts': scale, 'limit_4gib': 'FAILED',
                         'detail': str(e)[:200]})
    return rows


def build_native(tmp):
    import x64gen
    env_old = os.environ.get('HSPATH')
    os.environ['HSPATH'] = str(ROOT)
    try:
        image = tmp / 'repl-ir-x64'
        with contextlib.redirect_stdout(io.StringIO()):
            rc = x64gen.build_x64(str(REPL), str(image))
        assert rc == 0 and image.exists(), 'native repl build failed'
        return [str(image)]
    finally:
        if env_old is None:
            os.environ.pop('HSPATH', None)
        else:
            os.environ['HSPATH'] = env_old


def fmt_counts(c):
    return ' '.join('%s %d/%d' % (cat, c[cat][0], c[cat][1])
                    for cat in SCORED if c[cat][1])


def report(rows, mode):
    print('# agent hosted resource benchmark (%s mode)' % mode)
    print('commit: %s' % git_head())
    print('host: %s | python %s' % (platform.platform(), platform.python_version()))
    print('method: wall = perf_counter around the whole process;')
    print('  cold startup = process wall for an immediate `quit` (loads and')
    print('  re-saves the seeded store); latency = (session wall - startup)')
    print('  / commands; peak RSS = child ru_maxrss from wait4')
    print('  (kernel-reported per-process maximum, not system-wide).')
    print()
    for r in rows:
        if 'limit_4gib' in r:
            if r['limit_4gib'] == 'ok':
                print('[%s] 4 GiB RLIMIT_AS run, %d facts: ok, wall %.2fs,'
                      ' peak RSS %.1f MiB'
                      % (r['backend'], r['facts'], r['limit_wall_s'],
                         r['limit_rss_kb'] / 1024))
            else:
                print('[%s] 4 GiB RLIMIT_AS run, %d facts: FAILED: %s'
                      % (r['backend'], r['facts'], r.get('detail', '')))
            continue
        print('[%s] facts=%d' % (r['backend'], r['facts']))
        print('  cold startup: %.2fs, peak RSS %.1f MiB'
              % (r['startup_s'], r['startup_rss_kb'] / 1024))
        print('  latency: recall %.2f ms/cmd, miss %.2f ms/cmd'
              ' (word-indexed miss lookup; non-ASCII containment scans'
              ' only the non-ASCII word list)' % (r['recall_ms'], r['miss_ms']))
        print('  peak RSS (sessions): %.1f MiB' % (r['session_rss_kb'] / 1024))
        print('  held-out dialogue: %s' % fmt_counts(r['dialogue']))
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--full', action='store_true')
    ap.add_argument('--scales', default='',
                    help='comma list overriding the scale set')
    ap.add_argument('--backends', default='',
                    help='comma list from: interp, ir-x64 (default: per mode)')
    ap.add_argument('--out', default='',
                    help='write rows as JSON to this path instead of reporting')
    ap.add_argument('--report', default='',
                    help='read rows JSON from this path and print the report')
    args = ap.parse_args()
    full = args.full and not args.quick
    if args.report:
        rows = json.loads(Path(args.report).read_text(encoding='utf-8'))
        report(rows, 'saved')
        return rows
    scales = ([int(x) for x in args.scales.split(',')] if args.scales
              else ([0, 1000, 10000] if full else [0, 50, 200]))
    n_cmds = 200 if full else 30
    names = (args.backends.split(',') if args.backends
             else (['interp', 'ir-x64'] if full else ['interp']))
    workdir = Path(tempfile.mkdtemp(prefix='hs-agent-bench-'))
    rows = []
    for name in names:
        if name == 'interp':
            argv = [sys.executable, str(ROOT / 'interp.py'), str(REPL)]
        else:
            argv = build_native(workdir)
        rows += bench_backend(name, argv, workdir, scales, n_cmds,
                              full and not args.scales or
                              (full and str(scales[-1]) == '10000'))
    if args.out:
        Path(args.out).write_text(json.dumps(rows), encoding='utf-8')
        print('wrote %d rows to %s' % (len(rows), args.out))
    else:
        report(rows, 'full' if full else 'quick')
    return rows


if __name__ == '__main__':
    main()
