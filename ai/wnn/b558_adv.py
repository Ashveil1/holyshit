"""B-558 adversarial dev controls (parent review 2026-10-26): exact-substring name
anchoring collision classes. Reports wrong-but-stored answers (true stored fact,
question misread) SEPARATELY from fabricated facts (content not in store).
Classes: A nested names, B negation/uncertainty phrasing, C multi-entity,
D quoted/meta mention, E reversed roles."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hsml import HSML

FAILS = []
def check(cid, cond, detail):
    print(('PASS' if cond else 'FAIL'), cid, '' if cond else str(detail)[:200], flush=True)
    if not cond: FAILS.append(cid)

h = HSML(seed=0, assoc_fallback=True)  # B-558 harnesses explicitly opt into the EXPERIMENTAL layer (parent direction 2026-10-26: never default); probes byte-identical
# setup: nested names + normal facts
h.hear('กา มี จิ๊บ'); h.hear('กาโตะ มี ซ็อก'); h.hear('นก มี ปีก'); h.hear('วินนี่ มี โบ้')

# A: nested-name anchoring - longest exact surface must win; short name still reachable
r = h.hear('กาโตะมีอะไรบ้าง')
check('A1', r.get('kind') == 'assoc_answer' and 'ซ็อก' in (r.get('text') or ''), r)
r = h.hear('กา มีอะไรบ้าง')
check('A2', r.get('kind') == 'assoc_answer' and 'จิ๊บ' in (r.get('text') or '') and 'ซ็อก' not in (r.get('text') or ''), r)

# B: negation/uncertainty phrasing that matches NO designed frame - must not state facts
# (these are wrong-but-stored if answered: fact true, intent misread)
r = h.hear('นกไม่น่าจะมีปีกหรอก')
print('  B1 behavior:', r.get('kind'), repr(r.get('text'))[:70], flush=True)
check('B1', r.get('kind') != 'assoc_answer', 'wrong-but-stored: negation phrasing answered with facts')
r = h.hear('นกไม่มีปีกใช่ไหมนะ')
print('  B2 behavior:', r.get('kind'), repr(r.get('text'))[:70], flush=True)
check('B2', r.get('kind') != 'assoc_answer', 'wrong-but-stored: negation+question answered with facts')

# C: two taught entities in one sentence - layer must abstain (single-entity scope)
r = h.hear('นก กับ วินนี่ ต่างกันยังไง')
print('  C1 behavior:', r.get('kind'), repr(r.get('text'))[:70], flush=True)
check('C1', r.get('kind') != 'assoc_answer', 'wrong-but-stored: multi-entity answered as single')

# D: meta/quoted mention - not a request for facts
r = h.hear('เมื่อกี้คุณพูดถึงนกใช่ไหม')
print('  D1 behavior:', r.get('kind'), repr(r.get('text'))[:70], flush=True)
check('D1', r.get('kind') != 'assoc_answer', 'wrong-but-stored: meta mention answered with facts')

# E: reversed roles - attr-as-subject has no name anchor -> abstain
r = h.hear('ปีกมีอะไรบ้าง')
check('E1', r.get('kind') != 'assoc_answer', r)

print('FAILS:', len(FAILS), flush=True)
sys.exit(1 if FAILS else 0)
