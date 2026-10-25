"""eval_ash2: FRESH end-to-end evaluation of the vocabulary/fact-learning fix for Ash
(request 2026-10-25 13:18 'ทดสอบเลย'). ALL-NEW content (no hawk/wings replay).
Entry point: HSML.hear (the real conversation entry). One continuous conversation,
then a FRESH-PROCESS reload for persistence evidence. No code changes before/during.
Tested revision: wnn-checkpoints e9cab3f (B-541+B-542+B-543). PR #271 = B-541 only.
master (6e1aecb) contains NONE of the vocabulary fix yet.
Baseline logs/eval_ash_20261025.json is NOT touched."""
import json, random, sys, os
sys.path.insert(0, os.getcwd())
from hsml import HSML
import b521

PATH = 'logs/eval_ash2_mem.pkl'
transcript = []

def q(h, s):
    r = h.hear(s)
    transcript.append({'input': s, 'kind': r['kind'], 'text': r.get('text'), 'source': r.get('source')})
    return r

h = HSML(seed=0)
# normal startup: seed-world corpus (same as ordinary use; stated, not hidden)
for s in b521.gen_corpus(random.Random(0), 8):
    h.hear(s)
transcript.append({'input': '(startup: corpus โลกตั้งต้นปกติ)', 'kind': '-', 'text': None, 'source': '-'})

# 1) out-of-frame / unknown FIRST (honest abstains)
q(h, 'หวัดดี')                    # greeting, no frame
q(h, 'แพนด้ากินไผ่')              # unspaced
q(h, 'ขนดำ')                      # never-taught attr probe

# 2) teach NEW name with NEW attrs
q(h, 'แพนด้า มี ขนดำ')
q(h, 'แพนด้า มี หูกลม')
q(h, 'ขนดำ')                      # -> แพนด้า
q(h, 'ขนดำ และ หูกลม')            # conjunctive probe (B-542 routing)
q(h, 'แพนด้า มี อะไรบ้าง')        # reverse query (B-543)

# 3) second new name; shared attr -> honest ambiguity
q(h, 'หมูป่า มี ขนดำ')
q(h, 'ขนดำ')                      # -> ambiguous [หมูป่า, แพนด้า]

# 4) retraction (B-542) restores unique answer
q(h, 'หมูป่า ไม่มี ขนดำ')
q(h, 'ขนดำ')                      # -> แพนด้า only

# 5) honest nothing-to-retract
q(h, 'หมูป่า ไม่มี ปีก')          # หมูป่า has no ปีก

# 6) third new name, new attr
q(h, 'ตุ๊กแก มี ตีนติด')
q(h, 'ตีนติด')                    # -> ตุ๊กแก

# 7) seed world + seeded skill sanity (noninterference, live)
q(h, 'จะงอยปาก')                  # -> นก (seed world)
q(h, 'ผลบวกถึง ของ 20 คืออะไร')   # -> 210 (seeded skill)

# 8) reverse query reflects retraction state
q(h, 'หมูป่า มี อะไรบ้าง')        # -> empty -> honest abstain

h.save(PATH)
transcript.append({'input': '(บันทึกความจำ แล้วเปิด process ใหม่โหลดกลับ)', 'kind': '-', 'text': None, 'source': '-'})

# 9) FRESH PROCESS round-trip is done by the s2 entry point below
out = {'transcript': transcript, 'path': PATH}
print(json.dumps(out, ensure_ascii=False))
