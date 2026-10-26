"""BABY3 (P27): the requester's live-LLM caregiver version of the baby experiment. Same world, learner and criterion as baby2.py;
the only change is WHO TALKS: two LLM caregivers (OpenRouter free models) talk to each other about each scene in Thai,
and see + react to the baby's productions in later dialogue (contingent feedback through the language channel).
Baby learner: unchanged from-scratch Hebbian association (same code as baby2). Segmentation prior: caregivers are asked
to separate words with spaces (same 'tokens given' prior as baby2's pre-tokenized utterances).
Arms: 'llm' = implicit feedback only (baby hears replies); 'llmrew' = + explicit reward derived from reply content
(contains baby's word -> good, contains negation -> bad), matching baby2's reward magnitude. 'noncont' = baby reports
withheld from prompts (control for the feedback channel). Budget: 10 scenes per API call, 50 free calls/day cap.
python3 baby3.py ARM SEED [DAYS]   (caches every call in baby3_cache/; safe to rerun - resumes from cache)
"""
import random, json, os, sys, time, urllib.request
from collections import defaultdict
SIT = {'mae': 'แม่', 'pho': 'พ่อ', 'nom': 'นม', 'ball': 'ลูกบอล', 'cat': 'แมว', 'dog': 'หมา'}
SIT_EN = {'mae': 'mother', 'pho': 'father', 'nom': 'milk bottle', 'ball': 'ball', 'cat': 'cat', 'dog': 'dog'}
MODELS = ['google/gemma-4-31b-it:free', 'minimax/minimax-m3.1-flash:free']
CHUNK = 10
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'baby3_cache')
os.makedirs(CACHE, exist_ok=True)
def scene(rng):
    s = rng.choice(list(SIT)); s2 = rng.choice([x for x in SIT if x != s]) if rng.random() < 0.3 else None
    return s, {s, s2} - {None}
class Baby:
    def __init__(s): s.assoc = defaultdict(lambda: defaultdict(float)); s.wcnt = defaultdict(float); s.spoke = 0; s.heard = 0
    def hear(s, words, present):
        for w in words:
            s.wcnt[w] += 1; s.heard += 1
            for sit in SIT: s.assoc[w][sit] += 1.0 if sit in present else -0.25
    def reward(s, w, present, good):
        for sit in SIT:
            if w in SIT.values(): s.assoc[w][sit] += (2.0 if sit in present else -0.5) if good else (-1.0 if sit in present else 0.0)
    def say(s, present):
        best, bs = None, 0.5
        for w in SIT.values():
            sc = sum(s.assoc[w][sit] for sit in present) - 0.5 * sum(s.assoc[w][sit] for sit in SIT if sit not in present)
            if sc > bs: best, bs = w, sc
        return best
def call_llm(key, model, prompt, cache_key):
    cf = os.path.join(CACHE, cache_key + '.json')
    if os.path.exists(cf):
        return json.load(open(cf))['text']
    body = json.dumps({'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 900, 'temperature': 0.9}).encode()
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=body,
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429: raise RuntimeError('RATE_LIMITED')
        raise
    text = out['choices'][0]['message']['content']
    json.dump({'text': text}, open(cf, 'w'))
    return text
PROMPT_HEAD = """คุณกำลังเล่นเป็นพ่อกับแม่ของทารก คุยกันเองสั้นๆ เกี่ยวกับสิ่งที่เห็นในแต่ละฉาก ให้ทารกฟัง
กติกา: แยกทุกคำด้วยช่องว่างเดียว (เช่น แม่ จ๊ะ ดู นม สิ) - ตอบเป็น JSON array เท่านั้น หนึ่ง string ต่อฉาก โดยใช้รูปแบบ "A: ... | B: ..." (คุยกัน 1-2 ประโยคสั้นๆ ต่อคน บรรทัดเดียว)
ใช้คำว่า แม่ พ่อ นม ลูกบอล แมว หมา เมื่อพูดถึงสิ่งนั้นๆ พูดเหมือนคุยกันเองในบ้าน ไม่ต้องสอนทารกโดยตรง
"""
def chunk_prompt(scenes_desc, baby_notes):
    p = PROMPT_HEAD
    if baby_notes:
        p += '\nระหว่างฉากก่อนหน้า ทารกพูดว่า: ' + '; '.join(baby_notes) + ' - ตอบรับทารกตามธรรมชาติในบทคุย (ซ้ำคำ ถ้าถูก หรือแก้ให้ถูก)\n'
    p += '\nฉาก:\n' + '\n'.join(scenes_desc) + '\n\nตอบเป็น JSON array ของ string เท่านั้น ไม่ต้องมีคำอธิบาย'
    return p
def parse_lines(text, n):
    t = text.strip()
    if t.startswith('```'): t = t.split('\n', 1)[1].rsplit('```', 1)[0]
    try:
        arr = json.loads(t)
        arr = [str(x) for x in arr]
    except Exception:
        arr = [l.strip() for l in t.split('\n') if l.strip()]
    while len(arr) < n: arr.append('')
    return arr[:n]
def run(arm, seed, key, days=6, per_day=100):
    rng = random.Random(seed); b = Baby(); model = MODELS[seed % len(MODELS)]
    log = {'arm': arm, 'seed': seed, 'model': model, 'calls': 0}
    baby_notes = []
    for d in range(1, days + 1):
        day_scenes = [scene(rng) for _ in range(per_day)]
        for c0 in range(0, per_day, CHUNK):
            chunk = day_scenes[c0:c0 + CHUNK]
            desc = [f"{c0 + i + 1}. \u0e40\u0e2b\u0e47\u0e19: {SIT_EN[s]}" + (f" \u0e41\u0e25\u0e30 {SIT_EN[next(iter(present - {s}))]} \u0e14\u0e49\u0e27\u0e22" if len(present) > 1 else '') for i, (s, present) in enumerate(chunk)]
            text = call_llm(key, model, chunk_prompt(desc, baby_notes), f'{arm}_{seed}_d{d}_c{c0}')
            log['calls'] += 1
            baby_notes = []
            lines = parse_lines(text, len(chunk))
            for (s, present), line in zip(chunk, lines):
                words = [w.strip() for w in line.replace('A:', ' ').replace('B:', ' ').replace('|', ' ').split() if w.strip()]
                b.hear(words, present)
                if arm == 'noncont': continue
                w = b.say(present)
                if w is not None:
                    b.spoke += 1
                    baby_notes.append(f"'{w}' ({SIT_EN[s]})")
                    if arm == 'llmrew': b.reward(w, present, w == SIT[s])
            if len(baby_notes) > 6: baby_notes = baby_notes[-6:]
        r = random.Random(9000 + seed)
        rows = [scene(r) for _ in range(200)]
        n_m = sum(1 for s, _ in rows if s == 'mae'); n_nm = 200 - n_m
        mae = sum(b.say(p) == SIT['mae'] for s, p in rows if s == 'mae') / max(1, n_m)
        non = sum(b.say(p) == SIT['mae'] for s, p in rows if s != 'mae') / max(1, n_nm)
        hit = sum(b.say(p) == SIT[s] for s, p in rows) / 200
        print(f'day {d}: mae {mae:.2f} non {non:.2f} all6 {hit:.2f} spoke {b.spoke} heard {b.heard}', flush=True)
        if mae >= 0.8 and non <= 0.2:
            print(f'FIRST WORD day {d}: mae {mae:.2f} non {non:.2f} all6 {hit:.2f}', flush=True); return d, log
    print(f'no first word by day {days}: all6 {hit:.2f}', flush=True)
    return None, log
if __name__ == '__main__':
    arm = sys.argv[1]; seed = int(sys.argv[2]); days = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    key = open(sys.argv[4]).read().strip() if len(sys.argv) > 4 else os.environ.get('OR_KEY', '')
    try:
        res, log = run(arm, seed, key, days)
        print('RESULT', arm, seed, 'first-word day', res, log, flush=True)
    except RuntimeError as e:
        if str(e) == 'RATE_LIMITED': print('RATE_LIMITED - resume after daily reset (cache preserves progress)', flush=True); sys.exit(2)
        raise
