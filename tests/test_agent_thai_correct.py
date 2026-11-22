#!/usr/bin/env python3
"""A25.2 shape-scoped Thai correction, through the real native repl.

Positive, negative (state byte-identical), ambiguous (several old values),
alias target, and the unchanged English route. Corpus byte-identity with the
Python Oracle is in test_agent_core.py.
"""
import os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
fails = 0


def check(name, cond, detail=''):
    global fails
    print(('ok   ' if cond else 'FAIL ') + name + ('' if cond else ' ' + str(detail)[:500]))
    fails += 0 if cond else 1


tmp = tempfile.mkdtemp()
exe = os.path.join(tmp, 'repl')
r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build', str(ROOT / 'agent' / 'repl.holy'), '-o', exe],
                   capture_output=True, text=True, timeout=300)
assert r.returncode == 0, r.stderr[-800:]


def session(lines):
    d = tempfile.mkdtemp(dir=tmp)
    p = subprocess.run([exe], input='\n'.join(lines + ['quit']) + '\n', cwd=d, capture_output=True,
                       text=True, timeout=120)
    mem = Path(d, 'agent-memory.json')
    replies = p.stdout.split('\n')[1:1 + len(lines)]
    return replies, (mem.read_bytes() if mem.exists() else b'')


T = ['remember นกฮูก อยู่ ป่า', 'remember นกฮูก คือ นก', 'remember นกฮูก มี ปีก']
rep, _ = session(T + ['no, นกฮูก อยู่ สวน', 'what do you know about นกฮูก'])
check('positive: only the same-shape fact is replaced, others stay',
      rep[3] == 'updated นกฮูก อยู่ สวน' and rep[4] == 'i know นกฮูก is อยู่ สวน, คือ นก and มี ปีก', rep)
for cmd, want in (('no, ผี อยู่ วัด', 'nothing to correct: i do not know ผี'),
                  ('no, นกฮูก เป็น สัตว์', 'nothing to correct: นกฮูก has no เป็น fact')):
    rep0, mem0 = session(T)
    rep1, mem1 = session(T + [cmd])
    check('negative: ' + cmd + ' replies honestly', rep1[3] == want, rep1)
    check('negative: ' + cmd + ' leaves memory byte-identical', mem0 == mem1)
rep, _ = session(['remember ค อยู่ ก', 'remember ค is also อยู่ ข', 'no, ค อยู่ ง', 'what do you know about ค'])
check('ambiguous: several old values of one shape all replaced by the one new value, said so',
      rep[2] == 'updated ค อยู่ ง (replaced 2 earlier อยู่ facts)' and rep[3] == 'i know ค is อยู่ ง', rep)
rep, _ = session(T + ['ฮูก means นกฮูก', 'no, ฮูก อยู่ ถ้ำ', 'นกฮูก อยู่ไหน'])
check('alias: correction lands on the taught target', rep[4] == 'updated นกฮูก อยู่ ถ้ำ' and rep[5] == 'นกฮูก อยู่ ถ้ำ', rep)
rep, _ = session(T + ['no, นกฮูก is a bird', 'what do you know about นกฮูก'])
check('English route unchanged (replaces everything)', rep[3] == 'updated นกฮูก is a bird' and rep[4] == 'i know นกฮูก is a bird', rep)
rep, _ = session(['no, อยู่ ที่นี่', 'no, ก อยู่', 'no, ก is'])
check('malformed Thai corrections are not understood', all(x == 'i do not understand' for x in rep), rep)
print('%d failures' % fails)
sys.exit(1 if fails else 0)
