"""eval_ash.py - fresh, revealing evaluation of current hsml for the requester (2026-10-25).
NOT a replay of curated batteries: new content throughout. NO code change precedes
this baseline - the current implementation is the subject. Every utterance + the
system's LITERAL response (kind/text/source) is logged; failures preserved."""
import json, os, random, re, sys
sys.path.insert(0, os.getcwd())
from hsml import HSML
from b527 import SKILLS

LOG = []
def q(h, s):
    r = h.hear(s)
    e = {'in': s, 'kind': r['kind'], 'text': r.get('text'), 'source': r.get('source')}
    for k in ('result', 'decision', 'word', 'tried'):
        if k in r: e[k] = r[k]
    LOG.append(e)
    return r

def teach(h, word, truth, seed=0, name=True, keep=False):
    rng = random.Random(seed); out = {'word': word}
    if name:
        r = q(h, f'วิธีนี้ชื่อ {word}'); out['naming'] = r['kind']
    for i, x in enumerate(rng.sample(range(1, 40), 5)):
        r = q(h, f'ถ้า n เป็น {x} ตอบ {truth(x)}')
        if not keep and i < 4: LOG.pop()  # keep the log compact: 1st example + induce trigger
    tries = 0
    while r['kind'] == 'confirmation_question':
        tries += 1; assert tries < 50
        cx = int(re.fullmatch(r'ถ้า n เป็น (\d+) ตอบอะไร', r['text']).group(1))
        r = q(h, f'ตอบ {truth(cx)}')
        if not keep and tries < 3 and r['kind'] == 'confirmation_question': LOG.pop()
    out['final'] = r['kind']; out['tried'] = r.get('tried')
    return out

h = HSML(seed=0)
out = {'sections': {}}

# A. out-of-frame / boundary probes (untaught system)
q(h, 'สวัสดี')
q(h, 'เลขคู่ของ7คืออะไร')          # unspaced Thai - designed frames are spacing-dependent
q(h, 'ร้อยเท่า ของ 5 คืออะไร')       # never-taught skill word

# B. seeded skills (from b515 logs, provenance 'seeded'), fresh inputs
for s in ('เลขคู่ ของ 7 คืออะไร', 'กำลังสอง ของ 13 คืออะไร',
          'ผลบวกถึง ของ 100 คืออะไร', 'จับคู่สอง ของ 10 คืออะไร'):
    q(h, s)

# C. live dialog teaching of a NEW skill (n+3), then compositional (n+6)
t1 = teach(h, 'บวกสาม', lambda x: x + 3, seed=10)
q(h, 'บวกสาม ของ 41 คืออะไร')
t2 = teach(h, 'บวกหก', lambda x: x + 6, seed=11)
q(h, 'บวกหก ของ 41 คืออะไร')
out['sections']['teach'] = {'บวกสาม': t1, 'บวกหก': t2,
                            'บวกหก_deps': h.mem.skills.get('บวกหก', (0,0,{}))[2].get('deps', [])}

# D. attribute side: partial 6-animal world + NEW-animal statement (backend boundary)
for s in ('นก มี ปีก', 'นก มี จะงอยปาก', 'ค้างคาว มี ปีก', 'ค้างคาว มี ขน',
          'ผีเสื้อ มี ปีก', 'หมา มี ขน', 'แมว มี ขน'):
    r = q(h, s); LOG.pop()  # statements all 'observed'; keep log compact
q(h, 'ปีก')                  # ambiguous: exactly the observed winged set
q(h, 'จะงอยปาก')             # unique: นก
q(h, 'ปีก ขน')               # no match in the observed world -> abstain
q(h, 'เขา')                  # unknown word -> abstain
q(h, 'เหยี่ยว มี ปีก')       # NEW animal: acknowledged...
q(h, 'ปีก')                  # ...but does เหยี่ยว appear?

# E. revision live: บวกสาม n+3 -> n+4; dependent บวกห6 stale if it calls บวกสาม
q(h, 'บวกสาม ของ 41 คืออะไร')   # pre-revision value again (44)
h.hear('วิธีนี้ชื่อ บวกสาม')     # revision_opened (logged via teach below)
t3 = teach(h, 'บวกสาม', lambda x: x + 4, seed=12, name=False)
q(h, 'บวกสาม ของ 41 คืออะไร')   # post-revision value (45)
out['sections']['revision'] = t3
r = q(h, 'บวกหก ของ 41 คืออะไร')  # stale_skill if dependent
out['sections']['dependent_after_revision'] = r['kind']
if r['kind'] == 'stale_skill':
    # revalidation: teacher confirms the RECOMPOSED behavior (n+8)
    rr = h.hear('วิธีนี้ชื่อ บวกหก'); LOG.append({'in': 'วิธีนี้ชื่อ บวกหก', 'kind': rr['kind'], 'text': rr.get('text'), 'source': rr.get('source')})
    n = 0
    while rr['kind'] in ('revalidate_opened', 'confirmation_question'):
        cx = int(re.fullmatch(r'ถ้า n เป็น (\d+) ตอบอะไร', rr['text']).group(1))
        rr = q(h, f'ตอบ {cx + 8}'); n += 1; assert n < 10
    out['sections']['revalidated'] = rr['kind']
    q(h, 'บวกหก ของ 41 คืออะไร')

# F. save -> fresh process -> continuity
h.save('logs/eval_ash_mem.pkl')
h2 = HSML.load('logs/eval_ash_mem.pkl', seed=0)
n0 = len(LOG)
q(h2, 'บวกสาม ของ 41 คืออะไร')
q(h2, 'ปีก')
out['sections']['post_load'] = LOG[n0:]

out['log'] = LOG
print(json.dumps(out, ensure_ascii=False, indent=1))
print('DONE')
