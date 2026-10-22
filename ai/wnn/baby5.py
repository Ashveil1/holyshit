"""P29 (baby5.py): scaled baby - free conversation + unscripted situation stream, NO scene slots.
World: latent persistent THINGS (8 entities x 6 actions x 3 locations x 2 times) appear in the
situation stream as OPAQUE feature tokens (F0..F18) - persistent identity, no slot labels, no
semantics. Valid scenes sampled from world constraints (inanimates restricted). Per scene the baby
hears k=2..4 lines; each line is from pool A (here-and-now, about THIS scene) with prob f else
pool B (free conversation about anything). B lines heard during the scene = realistic dilution.
Learner: feature-token Hebbian association (word<->token, +1 present / -0.25 absent, as baby4)
- no slots, no clustering needed for grounding; token-class structure measured separately (P29b).
Chunk 1: world + mixer + TEMPLATE fallback pools (smoke test until LLM pools.json arrives) +
grounding accuracy vs dilution f. PRE-STAGED: C1 f=1.0 grounding >=.80; controls f=0 & shuffled <=.20."""
import random, json, sys
from collections import defaultdict
# --- world: 19 latent things, opaque tokens ---
ENT = ['mae', 'pho', 'maew', 'hma', 'ball', 'nom', 'khao', 'nok']
ACT = ['non', 'kin', 'wing', 'len', 'ma', 'pai']
LOC = ['ban', 'suan', 'rongrien']
TIM = ['chao', 'yen']
THINGS = [('E', e) for e in ENT] + [('A', a) for a in ACT] + [('L', l) for l in LOC] + [('T', t) for t in TIM]
TOK = {t: f'F{i}' for i, t in enumerate(THINGS)}          # harness-only mapping
TOKA = {v: k for k, v in TOK.items()}
ANIM = {'mae', 'pho', 'maew', 'hma', 'nok'}
VALID = [(e, a) for e in ENT for a in ACT if e in ANIM or a in ('len', 'ma')]
# Thai words for template fallback pools (LLM pools replace these)
WE = {'mae': 'แม่', 'pho': 'พ่อ', 'maew': 'แมว', 'hma': 'หมา', 'ball': 'ลูกบอล', 'nom': 'นม', 'khao': 'ข้าว', 'nok': 'นก'}
WA = {'non': 'นอน', 'kin': 'กิน', 'wing': 'วิ่ง', 'len': 'เล่น', 'ma': 'มา', 'pai': 'ไป'}
WL = {'ban': 'ที่บ้าน', 'suan': 'ที่สวน', 'rongrien': 'ที่โรงเรียน'}
FILL = ['จ๊ะ', 'ลูก', 'ดูสิ', 'นะ', 'ค่ะ', 'แล้ว', 'กำลัง', 'อยู่', 'ตรงนั้น']
FREE = ['วันนี้ อากาศ ร้อน มาก เลย', 'ข่าว เมื่อคืน น่าสนใจ จัง', 'พรุ่งนี้ ต้อง ไป ตลาด เช้า',
        'เลข สอง บวก สาม ได้ ห้า นะ', 'เรื่อง เมื่อวาน ตลก ดี', 'คืนนี้ ฝัน ดี นะ ลูก',
        'อาหาร เย็น นี้ อร่อย จัง', 'ประวัติ ศาสตร์ สนุก นะ', 'น้ำ หมด แล้ว ต้ม เพิ่ม',
        'โทรศัพท์ ดัง อีก แล้ว']
def template_pool_a(rng, e, a, l):
    w = [WE[e], WA[a], WL[l]]
    r = list(range(3)); rng.shuffle(r)
    line = [w[i] for i in r[:rng.choice((2, 3))]]
    return line + rng.sample(FILL, rng.choice((1, 2)))
def template_pool_b(rng):
    return rng.choice(FREE).split()
class World:
    def __init__(s, rng): s.rng = rng
    def scene(s):
        e, a = s.rng.choice(VALID); l = s.rng.choice(LOC); t = s.rng.choice(TIM)
        return (e, a, l, t)
    def tokens(s, sc): return {TOK[('E', sc[0])], TOK[('A', sc[1])], TOK[('L', sc[2])], TOK[('T', sc[3])]}
class Baby5:
    def __init__(s):
        s.assoc = defaultdict(lambda: defaultdict(float)); s.heard = 0
        s.tokcount = defaultdict(int)
    def hear(s, words, present):
        for w in words:
            s.heard += 1
            for tok in TOKA: s.assoc[w][tok] += 1.0 if tok in present else -0.25
        for tok in present: s.tokcount[tok] += 1
    def word_for(s, tok):
        best, bs = None, 0.5
        for w in s.assoc:
            sc = s.assoc[w][tok] - 0.5 * sum(s.assoc[w][o] for o in TOKA if o != tok)
            if sc > bs: best, bs = w, sc
        return best
    def best_tok(s, w):
        if w not in s.assoc: return None
        t, sc = max(s.assoc[w].items(), key=lambda kv: kv[1])
        tot = sum(max(0.0, v) for v in s.assoc[w].values())
        return t if sc > 0 and sc >= 1.5 * (tot - sc) else None
def run(seed, f, pool_a, pool_b, days=5, scenes_per_day=100, shuffle=False):
    rng = random.Random(2000 + seed); w = World(rng); b = Baby5()
    wr = random.Random(999) if shuffle else None
    for day in range(days):
        for _ in range(scenes_per_day):
            sc = w.scene(); pres = w.tokens(sc)
            for _ in range(rng.choice((2, 3, 4))):
                line = pool_a(rng, sc) if rng.random() < f else pool_b(rng)
                if shuffle: wr.shuffle(line)
                b.hear(line, pres)
    # grounding eval: for each thing, does word_for(token) recover the right Thai word?
    # harness-only mapping: entity tokens -> WE, action tokens -> WA (loc/time tokens unscored)
    ok, tot = 0, 0
    for e in ENT:
        tot += 1; ok += b.word_for(TOK[('E', e)]) == WE[e]
    for a in ACT:
        tot += 1; ok += b.word_for(TOK[('A', a)]) == WA[a]
    return ok, tot
if __name__ == '__main__':
    for f in (1.0, 0.5, 0.2, 0.0):
        accs = []
        for seed in range(5):
            ok, tot = run(seed, f, lambda r, sc: template_pool_a(r, sc[0], sc[1], sc[2]), template_pool_b)
            accs.append(ok / tot)
        print(f'f={f}: grounding {sum(accs)/len(accs):.2f} (per-seed {["%.2f"%a for a in accs]}, n={tot})', flush=True)
