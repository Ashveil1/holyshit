#!/usr/bin/env python3
"""A22.0 integrity tests: OS-level audit of the full learned-pattern
lifecycle (shadow, review, approve, activate, use, revoke) on the native
repl, run in a network-less namespace under strace. Directory snapshots
miss transient writes and symlink escapes; strace sees every open,
rename, unlink, link, symlink, mkdir and socket call.

Also: manifest change detection, hash-algorithm invalidation (L13) are
covered in test_agent_learned.py. Everything here is change detection,
not tamper resistance (poly62 hash, no trust anchor).
"""
import os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
import test_agent_review as rv
from test_agent_shadow import OWN_HAS, run

ALLOWED = {'agent-memory.json', 'agent-patterns.json',
           'agent-patterns.json.tmp', 'agent-attestations.json',
           'agent-attestations.json.tmp', 'agent-delegation.json',
           'agent-learned-log.json', 'agent-manifest.json',
           'agent-tripwire.json', 'agent-tripwire.json.tmp'}
TRACE = ('openat,open,creat,rename,renameat,renameat2,unlink,unlinkat,'
         'mkdir,mkdirat,symlink,symlinkat,link,linkat,truncate,socket,'
         'connect,bind')
WRITE_FLAGS = ('O_WRONLY', 'O_RDWR', 'O_CREAT', 'O_TRUNC', 'O_APPEND')


def audit(log, cwd):
    """Return (violations, writes) from an strace log."""
    bad, writes = [], set()
    cwd = str(Path(cwd).resolve())

    def path_ok(p):
        full = os.path.normpath(p if p.startswith('/') else cwd + '/' + p)
        if full == '/dev/null':
            return True
        return os.path.dirname(full) == cwd and \
            os.path.basename(full) in ALLOWED

    for line in log.splitlines():
        m = re.search(r'\b(socket|connect|bind)\(', line)
        if m:
            bad.append('network call: ' + line.strip()[:120])
            continue
        if re.search(r'= -1 E', line):
            continue
        m = re.search(r'\b(openat|open)\((?:AT_FDCWD, )?"([^"]*)", ([A-Z_|]+)',
                      line)
        if m:
            if any(f in m.group(3) for f in WRITE_FLAGS):
                writes.add(m.group(2))
                if not path_ok(m.group(2)):
                    bad.append('write outside allowlist: ' + m.group(2))
            continue
        m = re.search(r'\b(creat|rename|renameat|renameat2|unlink|unlinkat|'
                      r'mkdir|mkdirat|symlink|symlinkat|link|linkat|'
                      r'truncate)\(', line)
        if m:
            for p in re.findall(r'"([^"]*)"', line):
                writes.add(p)
                if not path_ok(p):
                    bad.append(m.group(1) + ' touches ' + p)
    return bad, writes


def traced(img, cwd, lines, env, tag):
    logf = Path(cwd).parent / ('strace-%s.log' % tag)
    argv = ['unshare', '-rn', 'strace', '-f', '-qq', '-e', 'trace=' + TRACE,
            '-o', str(logf), str(img)]
    r = subprocess.run(argv, input='\n'.join(lines) + '\n', cwd=str(cwd),
                       capture_output=True, text=True, env=env, timeout=300)
    assert r.returncode == 0, (r.stderr[-500:], r.stdout[-300:])
    return r.stdout, logf.read_text()


def main():
    for tool in ('unshare', 'strace'):
        if not shutil.which(tool):
            print('skip: %s unavailable' % tool)
            return
    env = dict(os.environ)
    env['HSPATH'] = str(ROOT)
    # negative controls: the auditor must flag bad calls
    b, _ = audit('1 socket(AF_INET, SOCK_STREAM, 0) = 3\n', '/tmp/x')
    assert b, 'auditor missed a socket call'
    b, _ = audit('1 openat(AT_FDCWD, "/etc/x", O_WRONLY|O_CREAT, 0666) = 3\n',
                 '/tmp/x')
    assert b, 'auditor missed an outside write'
    b, _ = audit('1 symlinkat("/etc/passwd", AT_FDCWD, "agent-patterns.json") '
                 '= 0\n', '/tmp/x')
    assert b, 'auditor missed a symlink escape'
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        img = td / 'repl'
        r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build',
                            str(ROOT / 'agent' / 'repl.holy'), '-o',
                            str(img)], capture_output=True, text=True,
                           env=env)
        assert r.returncode == 0, r.stderr[-400:]
        d = td / 'work'
        rv.setup(d, {'own.json': rv.own('has')})
        lines = ['patterns derive own.json', 'patterns shadow ' + OWN_HAS]
        for i in range(55):
            lines += [rv.rd(i), 'patterns origin r%d o%d verified_independent'
                      % (i, i % 5)]
        lines += [rv.RV, 'quit']
        out0, log0 = traced(img, d, lines, env, 'build')
        f = [rv.att(d, out0, 'fa', 'run1', 'dep1'),
             rv.att(d, out0, 'fb', 'run2', 'dep2')]
        rv.deleg(d)
        act = 'patterns activate ' + OWN_HAS
        lines = (['patterns manifest accept', 'patterns delegate del.json'] +
                 ['patterns attest %s %s owner' % (OWN_HAS, x) for x in f] +
                 ['patterns approve ' + OWN_HAS, act,
                  'read z1: a finch owns a nest. a kiwi is a bird',
                  'patterns learned', 'patterns revoke ' + OWN_HAS,
                  'read z2: a lark owns a nest', 'quit'])
        out1, log1 = traced(img, d, lines, env, 'use')
        assert 'activated ' + OWN_HAS in out1 and \
            '1 learned-pattern readings recorded' in out1
        for tag, log in (('build', log0), ('use', log1)):
            bad, writes = audit(log, d)
            assert not bad, (tag, bad[:5])
            names = {os.path.basename(w) for w in writes}
            assert 'agent-patterns.json' in names, (tag, names)
            assert names <= ALLOWED | {'/dev/null', 'null'}, (tag, names)
            assert not re.search(r'\b(socket|connect)\(', log)
        assert 'agent-manifest.json' in log1
        print('ok A22.0: no network syscalls; writes confined to the '
              'working-directory allowlist (%d + %d traced files)'
              % (len(audit(log0, d)[1]), len(audit(log1, d)[1])))
    print('all agent integrity tests passed')


if __name__ == '__main__':
    main()
