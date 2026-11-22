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
    ('remember my cat is somchai', 'remembered my cat is somchai (filed as a kind-of)', 'teach'),
    ('remember แมว is สัตว์เลี้ยง', 'remembered แมว is สัตว์เลี้ยง (filed as a kind-of)', 'teach'),
    ('remember bangkok is the capital of thailand',
     'remembered bangkok is the capital of thailand (filed as a kind-of)', 'teach'),
    ('remember กรุงเทพ is เมืองหลวง', 'remembered กรุงเทพ is เมืองหลวง (filed as a kind-of)', 'teach'),
    ('remember thai person is someone from thailand',
     'remembered thai person is someone from thailand (filed as a kind-of)', 'teach'),
    ('remember สัตว์เลี้ยง is pet', 'remembered สัตว์เลี้ยง is pet (filed as a kind-of)', 'teach'),
    ('remember red car is fast', 'remembered red car is fast (filed as a kind-of)', 'teach'),
    ('kitty means my cat', 'ok, kitty means my cat', 'teach'),
    ('คนไทย means thai person', 'ok, คนไทย means thai person', 'teach'),
    ('what is my cat', 'i know my cat is somchai', 'recall'),
    ('do you know bangkok', 'i know bangkok is the capital of thailand', 'recall'),
    ('what is แมว', 'i know แมว is สัตว์เลี้ยง', 'recall'),
    ('what is kitty', 'i know my cat is somchai', 'recall'),
    ('what is คนไทย', 'i know thai person is someone from thailand', 'recall'),
    ('no, my cat is milo', 'updated my cat is milo (filed as a kind-of)', 'correction'),
    ('what is my cat', 'i know my cat is milo', 'recall'),
    ('what is car', 'did you mean red car?', 'clarify'),
    ('yes', 'i know red car is fast', 'clarify'),
    ('what about it', 'i know red car is fast', 'recall'),
    ('what is สัตว์', 'did you mean สัตว์เลี้ยง?', 'clarify'),
    ('สัตว์เลี้ยง', 'i know สัตว์เลี้ยง is pet', 'clarify'),
    ('what is the moon', 'i do not know the moon', 'miss'),
    ('what is ดวงจันทร์', 'i do not know ดวงจันทร์', 'miss'),
    ('what is the capital of thailand',
     'i was never taught the capital of thailand, but from how you used it, '
     'the capital of thailand seems related to bangkok, thai and person',
     'usage'),
    ('hello', 'hello - teach me something with: remember <thing> is <fact>',
     'pleasantry'),
    ('สวัสดี', 'สวัสดี - สอนผมได้ด้วย: remember <thing> is <fact>',
     'pleasantry'),
    ('how is bangkok', 'all i know about bangkok is the capital of thailand',
     'open'),
    ('what else', 'that is all i know about bangkok', 'chain'),
    ('and my cat', 'i know my cat is milo', 'chain'),
    ('แมว คืออะไร', 'i know แมว is สัตว์เลี้ยง', 'open'),
    ('remember paris is in france', 'remembered paris is in france', 'teach'),
    ('remember france is in europe', 'remembered france is in europe', 'teach'),
    ('is paris in europe', 'yes: paris is in france, france is in europe',
     'inference'),
    ('is paris in asia', 'not that i know', 'inference'),
    ('where is paris', 'paris is in france, france is in europe', 'inference'),
    ('what does kitty mean', 'kitty means my cat', 'inference'),
    ('what does mean mean',
     'mean means the definitional relation: X mean Y says the definition of X is Y',
     'inference'),
    # แมว is already a key, so the additive teach answers 'added:'.
    ('remember แมว อยู่ สวน', 'added: แมว อยู่ สวน', 'teach'),
    ('แมว อยู่ไหน', 'แมว อยู่ สวน', 'inference'),
    # 'fond of fish' matches no relation shape, so it files a bare
    # kind-of edge and the reply says so.
    ('remember milo is fond of fish',
     'remembered milo is fond of fish (filed as a kind-of)', 'teach'),
    ('what is fish',
     'i was never taught fish, but from how you used it, fish seems related '
     'to milo and fond',
     'usage'),
    ('blorf zingle', 'i do not understand', 'unparsed'),
]
DIALOGUE += [
    # A13: typed verb relations, inheritance over is-a, three-valued
    # answers, contradiction handling, passive voice. Teaches set up
    # the world; questions are scored per category.
    ('remember a dog is a mammal', 'remembered a dog is a mammal', 'teach'),
    ('remember a mammal is an animal', 'remembered a mammal is an animal', 'teach'),
    ('remember an animal is a living thing', 'remembered an animal is a living thing', 'teach'),
    ('remember a living thing needs energy', 'remembered a living thing needs energy', 'teach'),
    ('remember a human can learn', 'remembered a human can learn', 'teach'),
    ('remember a doctor is a human', 'remembered a doctor is a human', 'teach'),
    ('remember a doctor is a professional', 'added: a doctor is a professional', 'teach'),
    ('does dog need energy',
     'yes: a dog is a mammal, a mammal is an animal, an animal is a '
     'living thing, a living thing needs energy', 'infer'),
    ('is energy needed by a dog',
     'yes: a dog is a mammal, a mammal is an animal, an animal is a '
     'living thing, a living thing needs energy', 'passive'),
    ('can a doctor learn', 'yes: a doctor is a human, a human can learn', 'infer'),
    ('does dog need sleep', 'not that i know', 'unknown'),
    ('what is a doctor', 'i know a doctor is a human and a professional', 'recall'),
    ('remember a fish cannot fly', 'remembered a fish cannot fly', 'teach'),
    ('can a fish fly', 'no: a fish cannot fly (taught)', 'negative'),
    ('can a fish swim', 'not that i know', 'unknown'),
    ('remember a bat is a mammal', 'remembered a bat is a mammal', 'teach'),
    ('remember a bat is not a mammal',
     'added: a bat is not a mammal (warning: this contradicts what you '
     'taught me earlier - i hold both and will say so when asked)', 'teach'),
    ('is bat a mammal',
     'i was taught both: a bat is a mammal and a bat is not a mammal'
     ' - i cannot say which is true', 'contradiction'),
]
DIALOGUE += [
    # A14: compositional rules over typed relations, numbered-step
    # reasoning, the can-stays-can axiom, and a rule-derived positive
    # colliding with a taught negative (shown, never resolved).
    ('remember a car has an engine', 'remembered a car has an engine', 'teach'),
    ('remember an engine uses energy', 'remembered an engine uses energy', 'teach'),
    # A14.1: the rule subjects need verified machine domains (guards).
    ('remember a car is a machine',
     'added: a car is a machine', 'teach'),
    ('does a car use energy',
     'yes: a car uses energy. reasoning:\n'
     '(1) a car has an engine + an engine uses energy => a car uses energy [rule has+uses; domain: a car is a machine]',
     'rule'),
    ('remember energy can produce motion',
     'remembered energy can produce motion', 'teach'),
    ('remember an engine is a machine',
     'added: an engine is a machine', 'teach'),
    ('can a car produce motion',
     'yes: a car can produce motion. reasoning:\n'
     '(1) an engine uses energy + energy can produce motion => an engine can produce motion [rule uses+can; domain: an engine is a machine]\n'
     '(2) a car has an engine + an engine can produce motion => a car can produce motion [rule has+can; domain: a car is a machine]',
     'rule'),
    # 'can produce' evidence never answers a 'produces' question.
    ('does a car produce motion', 'not that i know', 'unknown'),
    ('remember a car does not use gasoline',
     'added: a car does not use gasoline', 'teach'),
    ('remember an engine uses gasoline', 'added: an engine uses gasoline', 'teach'),
    ('does a car use gasoline',
     'i was taught a car does not use gasoline, but the rules derive a car uses gasoline'
     ' - i cannot say which is true. reasoning:\n'
     '(1) a car has an engine + an engine uses gasoline => a car uses gasoline [rule has+uses; domain: a car is a machine]',
     'contradiction'),
    # A14.1: strict mode blocks an unverified domain and explains why;
    # explore mode fires conditionally and lists assumptions, which
    # never become facts (strict blocks the same world again after).
    ('remember a pilot has a license', 'remembered a pilot has a license', 'teach'),
    ('remember a license can expire', 'remembered a license can expire', 'teach'),
    ('can a pilot expire',
     'not that i know - rule has+can applies only to machines, and i do not know whether a pilot is a machine',
     'guard'),
    ('mode explore',
     'explore mode: compositional rules may fire on unverified domains; conclusions list their assumptions (this session only)',
     'guard'),
    ('remember a bike has a dynamo', 'remembered a bike has a dynamo', 'teach'),
    ('remember a dynamo can produce electricity',
     'remembered a dynamo can produce electricity', 'teach'),
    ('can a bike produce electricity',
     'yes, on 1 assumption: a bike can produce electricity. reasoning:\n'
     '(1) a bike has a dynamo + a dynamo can produce electricity => a bike can produce electricity [rule has+can]\n'
     'assumptions:\n'
     '(a) a bike is a machine - assumed at step 1, unverified',
     'guard'),
    ('mode strict',
     'strict mode: compositional rules need verified domains (this session only)',
     'guard'),
    ('can a bike produce electricity',
     'not that i know - rule has+can applies only to machines, and i do not know whether a bike is a machine',
     'guard'),
    # A15 hypothesis learning: explore-mode assumptions become
    # candidates; teaching retires them; candidates are never facts.
    ('mode explore',
     'explore mode: compositional rules may fire on unverified domains; conclusions list their assumptions (this session only)',
     'hypothesis'),
    ('remember a glider has a wing', 'remembered a glider has a wing', 'teach'),
    ('remember a wing can generate lift', 'remembered a wing can generate lift', 'teach'),
    ('can a glider generate lift',
     'yes, on 1 assumption: a glider can generate lift. reasoning:\n'
     '(1) a glider has a wing + a wing can generate lift => a glider can generate lift [rule has+can]\n'
     'assumptions:\n'
     '(a) a glider is a machine - assumed at step 1, unverified',
     'hypothesis'),
    ('hypotheses',
     '2 open hypotheses (unresolved candidates, not beliefs):\n'
     "(a) a bike is a machine - assumed once, first for 'can a bike produce electricity'\n"
     "(b) a glider is a machine - assumed once, first for 'can a glider generate lift'",
     'hypothesis'),
    ('remember a bike is a machine', 'added: a bike is a machine', 'teach'),
    ('hypotheses',
     '1 open hypothesis (unresolved candidates, not beliefs):\n'
     "(a) a glider is a machine - assumed once, first for 'can a glider generate lift'\n"
     'recently retired:\n'
     '- a bike is a machine (taught positive)',
     'hypothesis'),
    ('mode strict',
     'strict mode: compositional rules need verified domains (this session only)',
     'hypothesis'),
    ('can a bike produce electricity',
     'yes: a bike can produce electricity. reasoning:\n'
     '(1) a bike has a dynamo + a dynamo can produce electricity => a bike can produce electricity [rule has+can; domain: a bike is a machine]',
     'hypothesis'),
]

SCORED = ('recall', 'clarify', 'miss', 'correction', 'pleasantry', 'open',
          'infer', 'passive', 'unknown', 'negative', 'contradiction',
          'rule', 'chain', 'inference', 'usage', 'unparsed', 'guard',
          'hypothesis')


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


def infer_script(store, n):
    # A13 inference latency: a verb-relation question that inherits
    # over the is-a graph. The synth store's bare is-a edges give it
    # a real graph to walk; there is no needs-edge, so every query
    # also exercises the honest UNKNOWN path.
    keys = store['order']
    if not keys:
        return []
    return ['does ' + keys[(j * 7919) % len(keys)] + ' need energy'
            for j in range(n)]


def derive_script(n):
    # A14 rule-derivation latency: a two-step composed proof (uses+can
    # feeding has+can), re-derived from scratch on every query - no
    # cross-query caching exists. The three teaches seed the world.
    setup = ['remember a car is a machine',
             'remember an engine is a machine',
             'remember a car has an engine',
             'remember an engine uses energy',
             'remember energy can produce motion']
    return setup + ['can a car produce motion'] * max(1, n - len(setup))


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
    # Replies can span several lines (A14 reasoning steps), so split
    # the stream by matching each expected reply (possibly multi-line)
    # in order. A mismatch consumes one line (the historical shape) so
    # later replies stay aligned; the final position assert catches
    # any drift. Banner, trailing '' and the closing 'bye' are dropped.
    body = stdout.split('\n')[1:-1]
    assert body and body[-1] == 'bye', (body[-3:], stdout[-400:])
    body = body[:-1]
    counts = {c: [0, 0] for c in SCORED}  # category -> [ok, total]
    pos = 0
    for line, want, cat in DIALOGUE:
        want_lines = want.split('\n')
        got_lines = body[pos:pos + len(want_lines)]
        got = '\n'.join(got_lines)
        if got == want:
            pos += len(want_lines)
        else:
            # Fallback for an unexpected reply: consume one line (the
            # historical single-line shape) so scoring stays aligned.
            got = body[pos] if pos < len(body) else '<missing>'
            pos += 1
            print('MISMATCH %r: want %r got %r' % (line, want, got))
        if cat in counts:
            counts[cat][1] += 1
            if got == want:
                counts[cat][0] += 1
    assert pos == len(body), (pos, len(body), body[pos:pos + 4])
    return counts


def bench_session(argv, cwd, store, script, label, rows, limit_bytes=None):
    (cwd / 'agent-memory.json').write_text(json.dumps(store, ensure_ascii=False),
                                           encoding='utf-8')
    stdin = '\n'.join(script + ['quit']) + '\n'
    wall, peak, out, rc, err = run_proc(argv, stdin, cwd, limit_bytes)
    assert rc == 0, (label, rc, err[-800:])
    return wall, peak, out


ALL_SESSIONS = ('startup', 'recall', 'miss', 'infer', 'derive', 'dialogue')


def bench_backend(name, argv, tmp, scales, n_cmds, limit_run,
                  only=ALL_SESSIONS):
    rows = []
    for scale in scales:
        store = synth_store(scale)
        d = tmp / ('%s-%d' % (name.replace('/', '_'), scale))
        d.mkdir()
        # Each field is measured by the same code path regardless of
        # the --sessions filter, so rows from chunked runs (long 10k
        # interp sessions split across invocations) merge field-wise;
        # session_rss_kb merges as the max.
        row = {'backend': name, 'facts': scale}
        rss_peaks = []
        # Latency is (session wall - startup wall), so the startup
        # session runs whenever any latency session does, even if it
        # was filtered out of the report fields.
        need_start = bool(set(only) & {'startup', 'recall', 'miss', 'infer', 'derive'})
        t_start = None
        if need_start:
            t_start, rss_start, _ = bench_session(argv, d, store, [], 'startup', rows)
            if 'startup' in only:
                row['startup_s'] = t_start
                row['startup_rss_kb'] = rss_start
        if 'recall' in only:
            n_rec_cmds = n_cmds if scale else n_cmds
            t_rec, rss_rec, _ = bench_session(argv, d, store,
                                              recall_script(store, n_rec_cmds), 'recall', rows)
            # max(0, ...): at scale 0 the recall session is quit-only and
            # scheduling noise can make the difference slightly negative.
            row['recall_ms'] = max(0.0, 1000.0 * (t_rec - t_start) / n_rec_cmds)
            rss_peaks.append(rss_rec)
        # Misses scan every taught key (no index): ~0.5 ms/key on the
        # interp route, so cap the miss count at large scales; the
        # per-command mean stays comparable.
        if 'miss' in only:
            n_mis_cmds = n_cmds if scale <= 1000 else 5
            t_mis, rss_mis, _ = bench_session(argv, d, store,
                                              miss_script(n_mis_cmds), 'miss', rows)
            row['miss_ms'] = max(0.0, 1000.0 * (t_mis - t_start) / n_mis_cmds)
            rss_peaks.append(rss_mis)
        if 'infer' in only:
            n_inf_cmds = n_cmds if scale else n_cmds
            t_inf, rss_inf, _ = bench_session(argv, d, store,
                                              infer_script(store, n_inf_cmds), 'infer', rows)
            row['infer_ms'] = max(0.0, 1000.0 * (t_inf - t_start) / n_inf_cmds)
            rss_peaks.append(rss_inf)
        if 'derive' in only:
            n_drv_cmds = n_cmds if scale else n_cmds
            t_drv, rss_drv, _ = bench_session(argv, d, store,
                                              derive_script(n_drv_cmds), 'derive', rows)
            row['derive_ms'] = max(0.0, 1000.0 * (t_drv - t_start) / n_drv_cmds)
            rss_peaks.append(rss_drv)
        if 'dialogue' in only:
            t_dlg, rss_dlg, out = bench_session(argv, d, store,
                                                dialogue_script(), 'dialogue', rows)
            row['dialogue'] = score_dialogue(out)
            rss_peaks.append(rss_dlg)
        if rss_peaks:
            row['session_rss_kb'] = max(rss_peaks)
        rows.append(row)
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
        if 'startup_s' in r:
            print('  cold startup: %.2fs, peak RSS %.1f MiB'
                  % (r['startup_s'], r['startup_rss_kb'] / 1024))
        lat_parts = []
        for key, label in (('recall_ms', 'recall'), ('miss_ms', 'miss'),
                           ('infer_ms', 'inference'), ('derive_ms', 'rule-derive')):
            if key in r:
                lat_parts.append('%s %.2f ms/cmd' % (label, r[key]))
        if lat_parts:
            print('  latency: ' + ', '.join(lat_parts) +
                  ' (word-indexed miss lookup; inheritance walks the is-a'
                  ' graph with O(1) edge checks; rule-derive is a two-step'
                  ' composed proof re-derived per query)')
        if 'session_rss_kb' in r:
            print('  peak RSS (sessions): %.1f MiB' % (r['session_rss_kb'] / 1024))
        if 'dialogue' in r:
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
    ap.add_argument('--sessions', default='',
                    help='comma subset of startup,recall,miss,infer,derive,'
                    'dialogue; for chunking long runs (rows merge field-wise)')
    ap.add_argument('--no-probe', action='store_true',
                    help='skip the 4 GiB limit probe')
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
    only = (tuple(args.sessions.split(',')) if args.sessions
            else ALL_SESSIONS)
    for s in only:
        assert s in ALL_SESSIONS, s
    workdir = Path(tempfile.mkdtemp(prefix='hs-agent-bench-'))
    rows = []
    for name in names:
        if name == 'interp':
            argv = [sys.executable, str(ROOT / 'interp.py'), str(REPL)]
        else:
            argv = build_native(workdir)
        rows += bench_backend(name, argv, workdir, scales, n_cmds,
                              (full and not args.no_probe and
                               (not args.scales or
                                str(scales[-1]) == '10000')), only)
    if args.out:
        Path(args.out).write_text(json.dumps(rows), encoding='utf-8')
        print('wrote %d rows to %s' % (len(rows), args.out))
    else:
        report(rows, 'full' if full else 'quick')
    return rows


if __name__ == '__main__':
    main()
