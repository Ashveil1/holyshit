"""b546.py - B-546 harness: Thai number words at the designed frame boundary.
C1 word==digit answers; C2 compounds; C3 full teaching with word examples +
word confirmations; C4 malformed abstains; C5 digit/glyph byte-identical +
b544 noninterference."""
import json, os, random, re, subprocess, sys
from hsml import HSML
import b521

DW = ['ศูนย์','หนึ่ง','สอง','สาม','สี่','ห้า','หก','เจ็ด','แปด','เก้า']
def thai_word(n):
    """Standard Thai rendering (harness-side only; the system never renders words)."""
    if n == 0: return 'ศูนย์'
    out = ''
    for w, p in (('ล้าน',1000000),('แสน',100000),('หมื่น',10000),('พัน',1000),('ร้อย',100)):
        d, n = divmod(n, p)
        if d: out += DW[d] + w
    tens, ones = divmod(n, 10)
    if tens == 2: out += 'ยี่สิบ'
    elif tens == 1: out += 'สิบ'
    elif tens: out += DW[tens] + 'สิบ'
    if ones:
        out += 'เอ็ด' if ones == 1 and (tens or out) else DW[ones]
    return out

def fresh(seed=0):
    h = HSML(seed=seed)
    for s in b521.gen_corpus(random.Random(0), 8): h.hear(s)
    return h

def s1():
    h = fresh()
    out = {}
    # C1: word-form identical to digit-form
    d = h.hear('เลขคู่ ของ 4 คืออะไร'); w = h.hear('เลขคู่ ของ สี่ คืออะไร')
    g = h.hear('เลขคู่ ของ ๔ คืออะไร')
    out['c1_digit'] = d.get('text'); out['c1_word'] = w.get('text'); out['c1_glyph'] = g.get('text')
    out['c1'] = (d.get('text') == w.get('text') == g.get('text') == 'เลขคู่ ของ 4 คือ 1'
                 and w['kind'] == 'skill_answer')
    # C2: compounds route to the right numbers
    c2 = {}
    # in execution range: word routes and answers identically to the digit value
    for q, expect in (('ผลบวกถึง ของ สิบ คืออะไร', 55), ('ผลบวกถึง ของ ยี่สิบ คืออะไร', 210),
                      ('ผลบวกถึง ของ สามสิบห้า คืออะไร', 630),
                      ('ผลบวกถึง ของ หนึ่งร้อยยี่สิบสาม คืออะไร', 7626)):
        r = h.hear(q)
        c2[q] = [r['kind'], r.get('result'), r.get('result') == expect and r['kind'] == 'skill_answer']
    # beyond the designed recursive-execution cap (CAPF=20000): parse is correct AND the
    # system abstains honestly at the execution bound (run-1 learning, recorded in LEDGER)
    from b527 import frame_num
    c2['parse_สองหมื่นห้า'] = [frame_num('สองหมื่นห้า'), frame_num('สองหมื่นห้า') == 20005]
    c2['parse_หนึ่งล้าน'] = [frame_num('หนึ่งล้าน'), frame_num('หนึ่งล้าน') == 1000000]
    r = h.hear('ผลบวกถึง ของ สองหมื่นห้า คืออะไร')
    c2['over_cap_abstains'] = [r['kind'], r.get('text'), r['kind'] == 'abstain' and r.get('text') is None]
    out['c2_detail'] = c2
    out['c2'] = all(v[-1] for v in c2.values())
    # C4: malformed abstains exactly as before
    c4 = {}
    for q in ('เลขคู่ ของ สี่สอง คืออะไร', 'เลขคู่ ของ สิบสิบ คืออะไร',
              'เลขคู่ ของ สามร้อยสองสิบสี่ห้า คืออะไร', 'เลขคู่ ของ แมว คืออะไร'):
        r = h.hear(q); c4[q] = [r['kind'], r.get('text')]
    out['c4_detail'] = c4
    out['c4'] = all(v[0] == 'abstain' and v[1] is None for v in c4.values())
    return out

def s2():
    h = fresh()
    out = {}
    assert thai_word(237) == 'สองร้อยสามสิบเจ็ด' and thai_word(11) == 'สิบเอ็ด' and thai_word(21) == 'ยี่สิบเอ็ด'
    r = h.hear('วิธีนี้ชื่อ สองเท่า')
    out['naming'] = r['kind']
    for x in (7, 2, 9, 4, 11):
        r = h.hear(f'ถ้า n เป็น {thai_word(x)} ตอบ {thai_word(2*x)}')
    tries = 0
    while r['kind'] == 'confirmation_question':
        tries += 1; assert tries < 30
        cx = int(re.fullmatch(r'ถ้า n เป็น (\d+) ตอบอะไร', r['text']).group(1))
        r = h.hear(f'ตอบ {thai_word(2*cx)}')   # word-form confirmation answer
    out['stored'] = [r['kind'], r.get('tried')]
    r = h.hear('สองเท่า ของ เก้าสิบเจ็ด คืออะไร')
    out['word_query'] = [r['kind'], r.get('text')]
    # persistence through save/load with a word-form query
    h.save('/tmp/b546_mem.pkl')
    h2 = HSML.load('/tmp/b546_mem.pkl', seed=0)
    r2 = h2.hear('สองเท่า ของ เก้าสิบเจ็ด คืออะไร')
    out['loaded_word_query'] = [r2['kind'], r2.get('text')]
    out['c3'] = (out['stored'][0] == 'skill_stored'
                 and out['word_query'] == ['skill_answer', 'สองเท่า ของ 97 คือ 194']
                 and out['loaded_word_query'] == ['skill_answer', 'สองเท่า ของ 97 คือ 194'])
    return out

def s3():
    out = {}
    # b544 storage-safety harness still passes (subprocess, own memory files)
    p = subprocess.run([sys.executable, '-u', 'b544.py'], capture_output=True, text=True)
    jline = next((ln for ln in p.stdout.strip().splitlines() if ln.startswith('{')), '')
    out['c5_b544'] = json.loads(jline)['verdict'] if p.returncode == 0 and jline else f'rc={p.returncode}: {p.stdout[-200:]} {p.stderr[-200:]}'
    out['c5'] = out['c5_b544'] == 'PASS'
    return out

if __name__ == '__main__':
    o1, o2, o3 = s1(), s2(), s3()
    checks = {k: v for d in (o1, o2, o3) for k, v in d.items() if k.startswith('c') and isinstance(v, bool)}
    print(json.dumps({'s1': o1, 's2': o2, 's3': o3,
                      'verdict': 'PASS' if all(checks.values()) else 'FAIL'}, ensure_ascii=False))
    print('DONE')
