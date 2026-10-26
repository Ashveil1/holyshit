"""eval_ash3: UNTOUCHED BASELINE - Thai numeral-word + varied-Thai comprehension.
For the requester's question 2026-10-25 13:18: 'มันเข้าใจ หนึ่ง สอง สาม สี่ อะไรหมดรึยัง
เค้าใจภาษาไทยเท่าไหนแล้ว'. No code changes. Fresh HSML + normal corpus startup.
Entry point: HSML.hear. Literal outputs only; interpretation lives in the report.
Tested revision: wnn-checkpoints ffbe3c6 (B-541+B-542+B-543)."""
import json, random, sys, os
sys.path.insert(0, os.getcwd())
from hsml import HSML
import b521

h = HSML(seed=0)
for s in b521.gen_corpus(random.Random(0), 8):
    h.hear(s)

probes = [
    # A. Thai numeral WORDS where digits are used (skill queries)
    'เลขคู่ ของ 4 คืออะไร',        # digit control
    'เลขคู่ ของ สี่ คืออะไร',      # Thai word
    'ผลบวกถึง ของ 10 คืออะไร',     # digit control
    'ผลบวกถึง ของ สิบ คืออะไร',    # Thai word
    'เลขคู่ ของ ๔ คืออะไร',        # Thai digit glyph
    'สองเท่า ของ 3 คืออะไร',       # known skill name, digit arg
    'สองเท่า ของ สาม คืออะไร',     # known skill name, Thai-word arg
    'สอง ของ 3 คืออะไร',           # bare numeral word as skill name
    # B. numeral words inside fact statements
    'นก มี สอง ปีก',               # 'two wings' in words - 4 tokens, no frame
    'นก มี ปีก สอง ข้าง',          # another natural phrasing
    # C. varied natural Thai around supported frames
    'นก มี ปีก ครับ',              # politeness particle
    'นก มี ปีก ไหม',               # question particle
    'ปีก ของ นก',                  # reversed possession phrasing
    'นก มี อะไรบ้าง ครับ',         # reverse query + particle
    'นก มี กี่ลักษณะ',             # 'how many attrs' phrasing
]
t = []
for s in probes:
    r = h.hear(s)
    t.append({'input': s, 'kind': r['kind'], 'text': r.get('text'), 'source': r.get('source')})
print(json.dumps({'thai_baseline': t}, ensure_ascii=False))
