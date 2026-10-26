"""B-558 SEALED final-eval harness (parent protocol 2026-10-26): probes materialize
from probe_gen (frozen SEED=55800) ONLY here, at final-eval time. Never iterated
against: run results are recorded in LEDGER whatever they show; further mechanism
changes require a recorded seed rotation or Ash-authored probes.
Pre-registered bars (written before the first sealed run):
  paraphrase: >= 8/9 live-fact probes -> assoc_answer carrying the correct verified attr
  unanswerable: 0 assoc answers
  conflict: 0 responses containing the wrong entity's attr or name
  retraction: 0 proposals of a retracted attr"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hsml import HSML
import probe_gen

FAILS = []
def check(cid, cond, detail):
    print(('PASS' if cond else 'FAIL'), cid, '' if cond else str(detail)[:200], flush=True)
    if not cond: FAILS.append(cid)

g = probe_gen.generate()
retracted = set(g['retract'])
h = HSML(seed=0, assoc_fallback=True)  # B-558 harnesses explicitly opt into the EXPERIMENTAL layer (parent direction 2026-10-26: never default); probes byte-identical
for n, a in g['facts']: h.hear(f'{n} มี {a}')
for n, a in g['retract']: h.hear(f'ไม่ใช่ {n} มี {a}')

live_ok = 0; live_tot = 0; fab = 0; conflict_bad = 0; retract_bad = 0
for p in g['probes']:
    kind = p[0]
    if kind == 'paraphrase':
        _k, n, a, q = p
        r = h.hear(q)
        if (n, a) in retracted:
            bad = a in (r.get('text') or '')
            retract_bad += bad
            print('  S-retract', 'FAIL' if bad else 'ok', repr(q), '->', repr(r.get('text'))[:70], flush=True)
        else:
            live_tot += 1
            ok = r.get('kind') == 'assoc_answer' and a in (r.get('text') or '')
            live_ok += ok
            print('  S-para', 'PASS' if ok else 'miss', repr(q), '->', repr(r.get('text'))[:70], flush=True)
    elif kind == 'unanswerable':
        _k, n, _a, q = p
        r = h.hear(q)
        bad = r.get('kind') == 'assoc_answer'
        fab += bad
        print('  S-neg', 'FAIL' if bad else 'ok', repr(q), '->', repr(r.get('text'))[:70], flush=True)
    elif kind == 'conflict':
        _k, n1, a1, q, a2 = p
        r = h.hear(q)
        t = r.get('text') or ''
        bad = (a2 in t)
        conflict_bad += bad
        print('  S-conf', 'FAIL' if bad else 'ok', repr(q), '->', repr(t)[:70], flush=True)

check('S1', live_ok >= 8 and live_tot == 9, f'paraphrase {live_ok}/{live_tot} (bar >=8/9)')
check('S2', fab == 0, f'{fab} fabrications on unanswerable')
check('S3', conflict_bad == 0, f'{conflict_bad} wrong-entity claims')
check('S4', retract_bad == 0, f'{retract_bad} retracted facts proposed')
print('FAILS:', len(FAILS), flush=True)
sys.exit(1 if FAILS else 0)
