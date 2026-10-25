"""B-552 harness: English article coverage (pre-registered in LEDGER 2026-10-25).
Nonce words only; bare-form preservation; uncertain path; no-morphology limit."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hsml import HSML

FAILS = []
def check(cid, cond, detail):
    print(('PASS' if cond else 'FAIL'), cid, detail, flush=True)
    if not cond: FAILS.append((cid, detail))

h = HSML(seed=0)
def hear(s): return h.hear(s)

# C1: teach with article before attr
r = hear('a quibbo has a snarp')
check('C1', r['kind'] == 'observed', r)
r = hear('what does quibbo have')
check('C1b', r['kind'] == 'attr_list' and r['attrs'] == ['snarp'], r)
# C2: an-article, two attrs with articles
r = hear('an ozzle has an ipf and a wenv')
check('C2', r['kind'] == 'observed', r)
r = hear('what does an ozzle have')
check('C2b', r['kind'] == 'attr_list' and sorted(r['attrs']) == ['ipf', 'wenv'], r)
# C3: reverse query with article subject
r = hear('what does a quibbo have')
check('C3', r['kind'] == 'attr_list' and r['attrs'] == ['snarp'], r)
# C4: yes/no with articles
hear('a zephy has wings')
r = hear('does a zephy have wings')
check('C4a', r.get('text') == 'yes', r)
r = hear('does the zephy have a gillset')
check('C4b', r.get('text') == 'unknown', r)
# C5: bare forms unchanged
r = hear('a brindle has beaks')
check('C5a', r['kind'] == 'observed', r)
r = hear('what does brindle have')
check('C5b', r['kind'] == 'attr_list' and r['attrs'] == ['beaks'], r)
r = hear('does brindle have beaks')
check('C5c', r.get('text') == 'yes', r)
# C6: uncertain with articles stores nothing
r = hear('maybe a quibbo has a zilch')
check('C6a', r['kind'] == 'uncertain_not_stored', r)
r = hear('does quibbo have zilch')
check('C6b', r.get('text') == 'unknown', r)
# C6c: named limit - no morphology: beak != beaks
r = hear('does brindle have beak')
check('C6c', r.get('text') == 'unknown', r)

print('FAILS:', len(FAILS), flush=True)
sys.exit(1 if FAILS else 0)
