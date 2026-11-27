#!/usr/bin/env python3
"""A25.3 Thai pronoun clarification through the real native repl.
Positive, negative, taught-referent, question-only (memory byte-identical),
unsupported forms. Corpus parity with the Oracle is in test_agent_core.py."""
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
    return p.stdout.split('\n')[1:1 + len(lines)], (mem.read_bytes() if mem.exists() else b'')


NOTOP = 'clarify: which thing do you mean by %s? say its name'
FORMS = ['{} อยู่ไหน', '{} คืออะไร', '{} หมายความว่าอะไร', 'เกี่ยวกับ {}', '{} คือ สัตว์ หรือไม่', '{} เป็น สัตว์ ไหม', '{}เป็นสัตว์ไหม']
for w in ('มัน', 'เขา', 'เธอ', 'อันนั้น', 'ตัว นั้น', 'คน นี้', 'ที่ นั่น', 'นี่', 'โน่น'):
    ok = True
    for f in FORMS:
        rep, _ = session([f.format(w)])
        ok = ok and rep[0] == NOTOP % w
    check('positive, no topic: %s in all 7 forms asks which thing' % w, ok, rep)
rep, _ = session(['remember ค้างคาว อยู่ ถ้ำ', 'มัน อยู่ไหน', 'เกี่ยวกับ เขา', 'มัน คือ สัตว์ หรือไม่'])
check('positive, topic: offers the topic as a question only',
      all(x == 'did you mean ค้างคาว? clarify by saying the name' for x in rep[1:]), rep)
base = ['remember ค้างคาว อยู่ ถ้ำ', 'remember วิชัย คือ พ่อค้า']
_, m0 = session(base)
_, m1 = session(base + ['มัน อยู่ไหน', 'เขา คืออะไร', 'เกี่ยวกับ เธอ', 'มัน คือ สัตว์ หรือไม่'])
check('question only: memory byte-identical', m0 == m1)
rep, _ = session(base + ['มัน อยู่ไหน', 'what about it'])
check('question only: topic unchanged by the clarification', rep[3] == 'all i know about วิชัย is คือ พ่อค้า' or 'วิชัย' in rep[3], rep)
rep, _ = session(['remember มันฝรั่ง อยู่ ดิน', 'มันฝรั่ง อยู่ไหน', 'ช้าง อยู่ไหน', 'มันฝรั่ง คืออะไร'])
check('negative: pronoun inside a longer name, and unknown nouns, are not clarified',
      rep[1] == 'มันฝรั่ง อยู่ ดิน' and rep[2] == 'ไม่รู้จักครับ ช้าง' and 'clarif' not in rep[3] and 'did you mean' not in rep[3], rep)
rep, _ = session(['remember มัน อยู่ ที่นี่', 'มัน อยู่ไหน', 'forget มัน', 'มัน อยู่ไหน'])
check('taught referent resolves normally, then clarifies again after forget',
      rep[1] == 'มัน อยู่ ที่นี่' and rep[3] == NOTOP % 'มัน', rep)
rep, _ = session(['ที่ นั่น มี อะไร บ้าง', 'เธอ อยู่ ที่ไหน', 'คน นั้น คือ ใคร', 'remember มัน อยู่ ที่นี่ แล้ว'])
check('unsupported forms are not intercepted', all('clarif' not in x and 'did you mean' not in x for x in rep), rep)
print('%d failures' % fails)
sys.exit(1 if fails else 0)
