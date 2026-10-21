"""BABY3H: manual-relay driver for the live-LLM caregiver experiment (P27h). A blind helper agent writes the
caregiver dialogue; this script owns the world, the baby, the criterion, and the prompt text.
Usage:
  python3 baby3h.py init ARM SEED          -> prints first batch prompt (20 scenes)
  python3 baby3h.py step ARM SEED < file   -> feed helper's JSON array; prints next batch prompt (or day eval + next)
State: /tmp/baby3h_{arm}_{seed}.json (regenerate scenes deterministically from seed if lost). Log: baby3h_{arm}_{seed}.log here.
"""
import random, json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from baby3 import SIT, SIT_EN, Baby, parse_lines
PER_DAY, CHUNK, DAYS = 60, 60, 5
def gen_day(seed, d):
    rng = random.Random(seed * 1000 + d)
    out = []
    for _ in range(PER_DAY):
        s = rng.choice(list(SIT)); s2 = rng.choice([x for x in SIT if x != s]) if rng.random() < 0.3 else None
        out.append((s, sorted({s, s2} - {None})))
    return out
def st_path(arm, seed): return f'/tmp/baby3h_{arm}_{seed}.json'
def save(arm, seed, st): json.dump(st, open(st_path(arm, seed), 'w'))
def load(arm, seed): return json.load(open(st_path(arm, seed)))
PROMPT_HEAD = """คุณกำลังเล่นเป็นพ่อกับแม่ของทารก คุยกันเองสั้นๆ เกี่ยวกับสิ่งที่เห็นในแต่ละฉาก ให้ทารกฟัง
กติกา: แยกทุกคำด้วยช่องว่างเดียว (เช่น แม่ จ๊ะ ดู นม สิ) - ตอบเป็น JSON array เท่านั้น หนึ่ง string ต่อฉาก รูปแบบ "A: ... | B: ..." (คุยกัน 1-2 ประโยคสั้นๆ ต่อคน บรรทัดเดียว)
พูดเหมือนคุยกันเองในบ้าน ไม่ต้องสอนทารกโดยตรง - คำว่า ลูกบอล ให้เขียนติดกันเป็นคำเดียว ห้ามแยก
"""
def batch_prompt(arm, seed, d, c0, notes):
    day = gen_day(seed, d)
    chunk = day[c0:c0 + CHUNK]
    p = PROMPT_HEAD
    if notes and arm != 'noncont':
        p += '\nระหว่างฉากก่อนหน้า ทารกพูดว่า: ' + '; '.join(notes) + ' - ตอบรับทารกตามธรรมชาติในบทคุย (ซ้ำคำถ้าถูก หรือแก้ให้ถูก)\n'
    lines = []
    for i, (s, pr) in enumerate(chunk):
        d = f"{c0 + i + 1}. เห็น: {SIT_EN[s]}"
        if len(pr) > 1: d += f" และ {SIT_EN[[o for o in pr if o != s][0]]} ด้วย"
        lines.append(d)
    p += '\nฉาก:\n' + '\n'.join(lines)
    p += '\n\nตอบเป็น JSON array ของ string เท่านั้น ไม่ต้องมีคำอธิบาย'
    return p
def evaluate(b, seed):
    r = random.Random(9000 + seed)
    rows = []
    for _ in range(200):
        s = r.choice(list(SIT)); s2 = r.choice([x for x in SIT if x != s]) if r.random() < 0.3 else None
        rows.append((s, {s, s2} - {None}))
    n_m = sum(1 for s, _ in rows if s == 'mae')
    mae = sum(b.say(p) == SIT['mae'] for s, p in rows if s == 'mae') / max(1, n_m)
    non = sum(b.say(p) == SIT['mae'] for s, p in rows if s != 'mae') / max(1, 200 - n_m)
    hit = sum(b.say(p) == SIT[s] for s, p in rows) / 200
    return mae, non, hit
if __name__ == '__main__':
    cmd, arm, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    if cmd == 'init':
        st = {'d': 1, 'c0': 0, 'notes': [], 'baby': None, 'spoke': 0, 'first': None}
        save(arm, seed, st)
        print(batch_prompt(arm, seed, 1, 0, []))
    else:
        st = load(arm, seed)
        b = Baby()
        if st['baby']:
            bb = st['baby']; b.assoc.update({w: defaultdict(float, d2) for w, d2 in bb['assoc'].items()}); b.wcnt.update(bb['wcnt']); b.spoke = bb['spoke']; b.heard = bb['heard']
        text = sys.stdin.read()
        lines = parse_lines(text, CHUNK)
        day = gen_day(seed, st['d']); chunk = day[st['c0']:st['c0'] + CHUNK]
        notes = []
        logf = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'baby3h_{arm}_{seed}.log'), 'a')
        for (s, present), line in zip(chunk, lines):
            present = set(present)
            words = [w.strip() for w in line.replace('A:', ' ').replace('B:', ' ').replace('|', ' ').split() if w.strip()]
            b.hear(words, present)
            logf.write(f"d{st['d']}c{st['c0']} scene={s} heard={' '.join(words)}\n")
            if arm == 'noncont': continue
            w = b.say(present)
            if w is not None:
                b.spoke += 1; notes.append(f"'{w}' (ตอนเห็น {SIT_EN[s]})")
                if arm == 'llmrew': b.reward(w, present, w == SIT[s])
                logf.write(f'  baby said {w} (true {SIT[s]})\n')
        logf.close()
        if len(notes) > 6: notes = notes[-6:]
        st['notes'] = notes
        st['c0'] += CHUNK
        out = []
        if st['c0'] >= PER_DAY:
            mae, non, hit = evaluate(b, seed)
            out.append(f"DAY {st['d']} EVAL: mae {mae:.2f} non {non:.2f} all6 {hit:.2f} spoke {b.spoke} heard {b.heard}")
            if mae >= 0.8 and non <= 0.2 and st['first'] is None:
                st['first'] = st['d']; out.append(f"FIRST WORD DAY {st['d']} (mae {mae:.2f} non {non:.2f} all6 {hit:.2f})")
            st['d'] += 1; st['c0'] = 0
        st['baby'] = {'assoc': {w: dict(d2) for w, d2 in b.assoc.items()}, 'wcnt': dict(b.wcnt), 'spoke': b.spoke, 'heard': b.heard}
        save(arm, seed, st)
        if st['d'] > DAYS:
            out.append(f"DONE arm={arm} seed={seed} first-word day={st['first']}")
        else:
            out.append('NEXT BATCH:')
            out.append(batch_prompt(arm, seed, st['d'], st['c0'], st['notes']))
        print('\n'.join(out))
