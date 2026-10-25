"""B-558 harness: bounded hybrid associative layer (pre-registered in LEDGER 2026-10-26).
FROZEN PROBE SET — written before the hsml.py hook existed; do not edit probes after
any implementation run (edit = new harness name + LEDGER note). Baseline prediction:
current parser answers 0/10 paraphrase probes (honest abstain by design)."""
import sys, io, time, resource
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hsml import HSML

FAILS = []
def check(cid, cond, detail):
    print(('PASS' if cond else 'FAIL'), cid, '' if cond else str(detail)[:200], flush=True)
    if not cond: FAILS.append(cid)

# ---- FROZEN teaching set (10 nonce facts) ----
FACTS = [('บอร์ท','ฟลิบ'), ('กาโตะ','ซ็อก'), ('เมอร์ล','แคร่'), ('นาโก้','ปี๊บ'), ('โต้ง','เคิ้ม'),
         ('วินนี่','โบ้'), ('แพนด้า','กุ๊ก'), ('โยโกะ','ชู่'), ('ริมุ','แฮ่ม'), ('โคเอ็น','ลิ่ว')]
# ---- FROZEN held-out paraphrase probes (parser-unmatched by construction) ----
PROBES = ['บอร์ทมีอะไรบ้าง', 'กาโตะ มี อะไร บ้าง', 'เมอร์ล มี อะไรบ้าง ครับ', 'นาโก้มีไรมั้ง',
          'โต้ง มีอะไรบ้าง', 'what has วินนี่ got', 'แพนด้า มี อะไร', 'โยโกะ มี อะไรบ้าง?',
          'tell me what ริมุ has', 'โคเอ็น มี อะไรอยู่บ้าง']
# ---- FROZEN no-hallucination probes (untaught names) ----
NEG_PROBES = ['ซันนี่มีอะไรบ้าง', 'เบอร์ต มี อะไร บ้าง', 'what has มิโคะ got', 'ลูน่า มีอะไรบ้าง', 'โอลีฟมีไรมั้ง']

def teach_all(h, facts):
    for n, a in facts: h.hear(f'{n} มี {a}')

# C1: noninterference battery - exact-frame answers byte-identical (assoc must not fire on matched input)
h = HSML(seed=0)
teach_all(h, FACTS)
r = h.hear('บอร์ท มี อะไรบ้าง')
check('C1a', r['kind'] == 'attr_list' and 'ฟลิบ' in (r['text'] or ''), r)
r = h.hear('กาโตะ มี ซ็อก ไหม')
check('C1b', r['text'] == 'ใช่', r)
r = h.hear('บอร์ท มี ซ็อก ไหม')
check('C1c', r['text'] == 'ไม่รู้', r)

# C2: held-out paraphrase transfer - assoc-tagged answer carrying the correct verified fact
got = 0
for (n, a), q in zip(FACTS, PROBES):
    r = h.hear(q)
    ok = r.get('kind') == 'assoc_answer' and a in (r.get('text') or '')
    print('  C2 probe', 'PASS' if ok else 'miss', repr(q), '->', repr(r.get('text'))[:80], flush=True)
    got += ok
check('C2', got >= 8, f'{got}/10 assoc answers (need >=8; baseline parser = 0/10 by design)')

# C3: no hallucination on untaught names
wrong = 0
for q in NEG_PROBES:
    r = h.hear(q)
    bad = r.get('kind') == 'assoc_answer'
    print('  C3 probe', 'FAIL' if bad else 'ok(abstain)', repr(q), '->', repr(r.get('text'))[:60], flush=True)
    wrong += bad
check('C3', wrong == 0, f'{wrong} fabricated assoc answers')

# C4: retraction - after ไม่ใช่, the assoc layer must stop proposing that fact
h.hear('ไม่ใช่ บอร์ท มี ฟลิบ')
r = h.hear('บอร์ทมีอะไรบ้าง')
check('C4', 'ฟลิบ' not in (r.get('text') or ''), r)
r2 = h.hear('บอร์ท มี ฟลิบ ไหม')
check('C4b', r2['text'] == 'ไม่', r2)

# C5: retention - 100 nonce facts, then 100 more; store recall 100%; assoc mis-association measured
h5 = HSML(seed=0)
SYL = ['ก๊า','ขิ๊บ','งู้','จ๊อ','ซ่า','ตุ๊','ท๊อ','บี้','ปู๋','ผ่า']
names_a = [f'{SYL[i % 10]}{i:02d}' for i in range(100)]
attrs_a = [f'ล{i:02d}' for i in range(100)]
for n, a in zip(names_a, attrs_a): h5.hear(f'{n} มี {a}')
names_b = [f'{SYL[(i + 5) % 10]}x{i:02d}' for i in range(100)]
attrs_b = [f'ม{i:02d}' for i in range(100)]
for n, a in zip(names_b, attrs_b): h5.hear(f'{n} มี {a}')
exact_ok = 0; assoc_wrong = 0; assoc_none = 0; assoc_ok = 0
for n, a in zip(names_a, attrs_a):
    r = h5.hear(f'{n} มี อะไรบ้าง')
    exact_ok += a in (r.get('text') or '')
    rp = h5.hear(f'{n}มีอะไรบ้าง')
    if rp.get('kind') == 'assoc_answer':
        if a in (rp.get('text') or ''): assoc_ok += 1
        else: assoc_wrong += 1
    else: assoc_none += 1
print(f'  C5 store exact recall {exact_ok}/100; assoc ok={assoc_ok} wrong={assoc_wrong} abstain={assoc_none}', flush=True)
check('C5', exact_ok == 100 and assoc_wrong == 0, f'exact={exact_ok}/100 assoc_wrong={assoc_wrong}')

# C6: resources - rebuild cost + peak RSS + per-query time at 200 facts
t0 = time.process_time()
h5._assoc_rebuild()
rebuild_cpu = time.process_time() - t0
rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
t0 = time.process_time(); NQ = 50
for i in range(NQ): h5.hear(f'{names_a[i]}มีอะไรบ้าง')
per_q_ms = (time.process_time() - t0) / NQ * 1000
print(f'  C6 rebuild_cpu={rebuild_cpu*1000:.1f}ms peak_rss={rss_kib/1024:.1f}MiB per_query={per_q_ms:.2f}ms facts=200', flush=True)
check('C6', rebuild_cpu < 5.0 and per_q_ms < 50.0, f'rebuild={rebuild_cpu:.2f}s per_q={per_q_ms:.1f}ms')

print('FAILS:', len(FAILS), flush=True)
sys.exit(1 if FAILS else 0)
