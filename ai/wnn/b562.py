"""B-562: LEARNED sentence -> (intent, slots) mapping from dialogue teaching examples.
Pre-registered in LEDGER.md (B-562 + Amendment 1) BEFORE this code was written.
SUPPLIED (designed): tokenizer/encoder, protocol, intent inventory, confirmation acts,
  canonical reconstruction glue. LEARNED (from training dialogues only): feature->intent
  mapping (all arms), frame words, slot roles. NO pretrained models.
Arms: WNN (bleached WiSARD, learned candidate) / NB-1 (online multinomial NB a=1) /
  T2P-map (text2prog.py Learner's exact scoring rule: soft credit + log vote a=0.05 -
  text2prog2's learn_lexicon does NOT transfer: it needs an answer-oracle over a
  hypothesis space and learns word->digit substitutions; intent classification has
  no such oracle structure) / 1-NN cosine / majority / designed-frame router contrast.
Split is AUTHOR-GENERATED (not independent validation). Family-disjoint eval with
UNFAMILIAR entities/attrs/classes/skills/numbers never seen in training.
Usage: python3 b562.py           # full sweep, prints JSON lines + verdicts
"""
import json, math, random, re, resource
from collections import Counter, defaultdict

# ---------------- supplied: shared encoder (identical features, all arms) ----------------
def encode(s):
    f = Counter()
    for w in s.split():
        f['w:' + w] += 1
    t = s.replace(' ', '')
    for n in (2, 3, 4):
        for i in range(len(t) - n + 1):
            f['c:' + t[i:i + n]] += 1
    return f

BUCKET = 4096
def buckets(feats):
    return {hash(k) % BUCKET for k in feats}

# ---------------- learned-mapping arms ----------------
class WNN:  # bleached WiSARD discriminators, one per intent
    def __init__(self, intents, seed, R=32, T=6, bleach=1):
        rng = random.Random(seed); self.R, self.b = R, bleach
        self.maps = {d: [(tuple(rng.sample(range(BUCKET), T)), Counter()) for _ in range(R)] for d in intents}
    def add(self, feats, d):
        bs = buckets(feats)
        for sel, mem in self.maps[d]:
            mem[tuple(b in bs for b in sel)] += 1
    def scores(self, feats):
        bs = buckets(feats); out = {}
        for d, ms in self.maps.items():
            out[d] = sum(1 for sel, mem in ms if mem.get(tuple(b in bs for b in sel), 0) >= self.b)
        return out

class NB:  # online multinomial naive Bayes, alpha=1
    def __init__(self, intents, alpha=1.0):
        self.a = alpha; self.fc = {d: Counter() for d in intents}
        self.tot = Counter(); self.docs = Counter(); self.intents = list(intents)
    def add(self, feats, d):
        self.fc[d].update(feats); self.tot[d] += sum(feats.values()); self.docs[d] += 1
    def scores(self, feats):
        V = 50000; out = {}
        nd = sum(self.docs.values()) or 1
        for d in self.intents:
            s = math.log((self.docs[d] + 1) / (nd + len(self.intents)))
            den = self.tot[d] + self.a * V
            for f, c in feats.items():
                s += c * math.log((self.fc[d][f] + self.a) / den)
            out[d] = s
        return out

class T2P:  # text2prog.py Learner's exact rule: soft credit + log vote, alpha=0.05
    def __init__(self, intents):
        self.I = list(intents); self.cnt = defaultdict(lambda: defaultdict(float)); self.tot = defaultdict(float)
    def add(self, feats, d):
        for f, c in feats.items():
            self.tot[f] += c; self.cnt[f][d] += c
    def scores(self, feats):
        fs = [f for f in feats if f in self.tot]; out = {}
        for d in self.I:
            out[d] = sum(feats[f] * math.log((self.cnt[f].get(d, 0) + 0.05) / (self.tot[f] + 0.05 * len(self.I))) for f in fs)
        return out

class NN1:
    def __init__(self, intents): self.ex = []
    def add(self, feats, d): self.ex.append((feats, d))
    def scores(self, feats):
        out = Counter()
        for f2, d in self.ex:
            num = sum(min(c, f2[f]) for f, c in feats.items())
            den = math.sqrt(sum(c * c for c in feats.values())) * math.sqrt(sum(c * c for c in f2.values())) or 1
            out[d] = max(out[d], num / den)
        return dict(out)

ARMS = ['wnn', 'nb', 't2p', 'nn1']
def majority_scores(feats): return {}

# ---------------- data: intents, phrasing families (AUTHOR-GENERATED), vocab ----------------
INTENTS = ['teach_attr', 'ask_attr', 'retract_attr', 'teach_isa', 'is_a_q', 'name_skill', 'give_example', 'confirm_answer']
# each family: render(x, y) -> sentence; slots always (first, second) in GOLD role order
FAM = {
 'teach_attr': [lambda x, y: f'{x} มี {y}', lambda x, y: f'{x} นั้น มี {y}'],
 'ask_attr': [lambda x, y: f'{y} ของ {x} คืออะไร', lambda x, y: f'อยากรู้ {y} ของ {x}'],
 'retract_attr': [lambda x, y: f'{x} ไม่มี {y}', lambda x, y: f'{x} ไม่มี {y} เลย'],
 'teach_isa': [lambda x, y: f'{x} เป็น {y}', lambda x, y: f'{x} คือ {y} ประเภทหนึ่ง'],
 'is_a_q': [lambda x, y: f'{x} เป็น {y} ไหม', lambda x, y: f'{x} เป็น {y} หรือเปล่า'],
 'name_skill': [lambda x, y: f'{x}'],
 'give_example': [lambda x, y: f'ถ้า n เป็น {x} ตอบ {y}', lambda x, y: f'n คือ {x} ให้ตอบ {y}'],
 'confirm_answer': [lambda x, y: f'ตอบ {x}', lambda x, y: f'ตอบว่า {x}'],
}
DEV_FAM = {
 'teach_attr': lambda x, y: f'ดู {y} ของ {x}',
 'ask_attr': lambda x, y: f'บอก {y} ของ {x} หน่อย',
 'retract_attr': lambda x, y: f'ไม่จริง {x} ไม่มี {y}',
 'teach_isa': lambda x, y: f'{x} นับเป็น {y}',
 'is_a_q': lambda x, y: f'{x} ใช่ {y} ไหม',
 'name_skill': lambda x, y: f'{x} นะ',
 'give_example': lambda x, y: f'สมมติ n เป็น {x} ตอบ {y}',
 'confirm_answer': lambda x, y: f'ให้ตอบ {x}',
}
EVAL_FAM = {
 'teach_attr': [lambda x, y: f'{x} มี {y} ด้วย', lambda x, y: f'{y} ของ {x} สวย', lambda x, y: f'{x} has {y}'],
 'ask_attr': [lambda x, y: f'{y} ของ {x} ก็คืออะไร กัน', lambda x, y: f'what is the {y} of {x}'],
 'retract_attr': [lambda x, y: f'{x} ไม่เคยมี {y}', lambda x, y: f'{x} does not have {y}'],
 'teach_isa': [lambda x, y: f'{x} จัดเป็น {y}', lambda x, y: f'{x} is a {y}'],
 'is_a_q': [lambda x, y: f'{x} เป็น {y} จริงไหม', lambda x, y: f'is {x} a {y}'],
 'name_skill': [lambda x, y: f'{x} please', lambda x, y: f'สอนวิธี {x}'],
 'give_example': [lambda x, y: f'กรณี n เป็น {x} ตอบ {y} นะ', lambda x, y: f'if n is {x} answer {y}'],
 'confirm_answer': [lambda x, y: f'ตอบไปว่า {x} เลย', lambda x, y: f'answer {x}'],
}
VOCAB = {
 'teach_attr': (['มิโล', 'แมว', 'หมา', 'นก', 'ปลา', 'Milo', 'cat'], ['หาง', 'ปีก', 'ขา', 'ตา', 'หู', 'tail', 'wing']),
 'ask_attr': (['มิโล', 'แมว', 'หมา', 'นก', 'ปลา', 'Milo', 'cat'], ['หาง', 'ปีก', 'ขา', 'ตา', 'หู', 'tail', 'wing']),
 'retract_attr': (['มิโล', 'แมว', 'หมา', 'นก', 'ปลา'], ['หาง', 'ปีก', 'ขา', 'ตา', 'หู']),
 'teach_isa': (['มิโล', 'แมว', 'หมา', 'นก', 'Milo'], ['แมว', 'สัตว์', 'นก', 'cat', 'animal']),
 'is_a_q': (['มิโล', 'แมว', 'หมา', 'นก', 'Milo'], ['แมว', 'สัตว์', 'นก', 'cat', 'animal']),
 'name_skill': (['บวก', 'ลบ', 'คูณ', 'หาร'], [None]),
 'give_example': (['หนึ่ง', 'สอง', 'สาม', 'one', 'two'], ['สี่', 'ห้า', 'หก', 'four', 'five']),
 'confirm_answer': (['สี่', 'ห้า', 'หก', 'four', 'five'], [None]),
}
EVAL_VOCAB = {  # UNFAMILIAR at eval: never in any training/dev example
 'teach_attr': (['เหยี่ยว', 'กวาง', 'แพะ', 'tiger', 'bear'], ['เกล็ด', 'เขา', 'งา', 'horn', 'scale']),
 'ask_attr': (['เหยี่ยว', 'กวาง', 'แพะ', 'tiger', 'bear'], ['เกล็ด', 'เขา', 'งา', 'horn', 'scale']),
 'retract_attr': (['เหยี่ยว', 'กวาง', 'แพะ'], ['เกล็ด', 'เขา', 'งา']),
 'teach_isa': (['เหยี่ยว', 'กวาง', 'แพะ', 'tiger'], ['สัตว์เลี้ยง', 'แมลง', 'pet', 'insect']),
 'is_a_q': (['เหยี่ยว', 'กวาง', 'แพะ', 'tiger'], ['สัตว์เลี้ยง', 'แมลง', 'pet', 'insect']),
 'name_skill': (['ถอด', 'รวม'], [None]),
 'give_example': (['ยี่สิบ', 'ร้อย', 'twenty'], ['พัน', 'หมื่น', 'hundred']),
 'confirm_answer': (['พัน', 'หมื่น', 'hundred'], [None]),
}
WRONG_INTENT = ['วันนี้ อากาศ ดี มาก', 'ฉัน ชอบ กิน ข้าว', 'สบายดี ไหม', 'พรุ่งนี้ ฝน จะ ตก',
 'the weather is nice today', 'i like eating rice', 'how are you feeling', 'ลาก่อน แล้ว พบ กัน',
 'goodbye see you', 'อร่อย จัง เลย', 'very delicious food', 'นอน หลับ ฝัน ดี', 'good night sleep well',
 'เจ็บ คอ มาก', 'my head hurts', 'ราคา เท่าไหร่ กัน', 'too expensive for me', 'ขอบคุณ มาก ครับ',
 'thank you very much', 'ไม่ เป็นไร เลย']

def gen(rng, intent, fams, vocab, n):
    out = []
    xs, ys = vocab
    for _ in range(n):
        fi = rng.randrange(len(fams)); f = fams[fi]; x = rng.choice(xs)
        y = rng.choice(ys) if ys[0] is not None else None
        out.append((f(x, y), intent, tuple(v for v in (x, y) if v is not None), fi))
    return out

# ---------------- learned slot extraction (statistics from training examples ONLY) ----------------
def learn_slots(train):
    """frame words = tokens in >=50% of an intent's examples; slots = remaining tokens.
    role table: for each intent, filler -> most common slot POSITION across training (learned)."""
    by = defaultdict(list)
    for s, d, slots, _ in train: by[d].append(s)
    frame, rolepos = {}, defaultdict(lambda: defaultdict(Counter))
    for d, ss in by.items():
        c = Counter(w for s in ss for w in set(s.split()))
        thr = max(1, 0.5 * len(ss))
        frame[d] = {w for w, n in c.items() if n >= thr}
    for s, d, gold, _ in train:
        toks = [w for w in s.split() if w not in frame[d]]
        for pos, w in enumerate(toks):
            rolepos[d][w][pos] += 1
    return frame, rolepos

def extract_slots(s, d, frame, rolepos, nslots):
    toks = [w for w in s.split() if w not in frame[d]]
    if len(toks) < nslots: return None
    toks = toks[:nslots]
    # role assignment: prefer each token's learned typical position; fall back to surface order
    assigned = [None] * nslots; claimed = set()
    for w in toks:
        rp = rolepos[d].get(w)
        if rp:
            p = rp.most_common(1)[0][0]
            if p < nslots and assigned[p] is None:
                assigned[p] = w; claimed.add(w)
    leftover = [w for w in toks if w not in claimed]
    li = 0
    for p in range(nslots):
        if assigned[p] is None:
            assigned[p] = leftover[li] if li < len(leftover) else toks[p]; li += 1
    return tuple(assigned)

# ---------------- supplied glue: canonical reconstruction (named designed) ----------------
GLUE = {
 'teach_attr': lambda sl: f'{sl[0]} มี {sl[1]}',
 'ask_attr': lambda sl: f'{sl[1]} ของ {sl[0]} คืออะไร',
 'retract_attr': lambda sl: f'{sl[0]} ไม่มี {sl[1]}',
 'teach_isa': lambda sl: f'{sl[0]} เป็น {sl[1]}',
 'is_a_q': lambda sl: f'{sl[0]} เป็น {sl[1]} ไหม',
 'name_skill': lambda sl: f'{sl[0]}',
 'give_example': lambda sl: f'ถ้า n เป็น {sl[0]} ตอบ {sl[1]}',
 'confirm_answer': lambda sl: f'ตอบ {sl[0]}',
}
NSLOTS = {'teach_attr': 2, 'ask_attr': 2, 'retract_attr': 2, 'teach_isa': 2, 'is_a_q': 2,
          'name_skill': 1, 'give_example': 2, 'confirm_answer': 1}

def predict(mapper, feats, tau):
    sc = mapper.scores(feats)
    if not sc: return None, 0.0
    best = max(sc, key=sc.get)
    ranked = sorted(sc.values(), reverse=True)
    margin = ranked[0] - (ranked[1] if len(ranked) > 1 else 0)
    if sc[best] < tau: return None, margin
    return best, margin

def main():
    seeds = [0, 1, 2, 3, 4]; Ks = [1, 2, 4, 8]
    import hsml as H
    all_res = []
    for seed in seeds:
        rng = random.Random(1000 + seed)
        train_full = {d: gen(rng, d, FAM[d], VOCAB[d], 8) for d in INTENTS}
        dev = [it for d in INTENTS for it in gen(rng, d, [DEV_FAM[d]], VOCAB[d], 4)]
        dev += [(s, 'NONE', (), -1) for s in rng.sample(WRONG_INTENT, 8)]
        ev = [it for d in INTENTS for it in gen(rng, d, EVAL_FAM[d], EVAL_VOCAB[d], 8)]
        ev_wrong = [(s, 'NONE', (), -1) for s in [w for w in WRONG_INTENT if w not in {x[0] for x in dev}]]
        # dev: choose WNN bleach + abstain margin tau (frozen before eval)
        best_cfg, best_j = None, -1
        for bleach in (1, 2):
            for tau in (1, 2, 4):
                m = WNN(INTENTS, seed, bleach=bleach)
                for s, d, _, _ in [x for d in INTENTS for x in train_full[d]]: m.add(encode(s), d)
                ok = n = 0
                for s, d, _, _ in dev:
                    p, mg = predict(m, encode(s), tau)
                    ok += (p == d) if d != 'NONE' else (p is None); n += 1
                if ok / n > best_j: best_j, best_cfg = ok / n, (bleach, tau)
        bleach, tau = best_cfg
        for k in Ks:
            train = [(s, d, sl, fi) for d in INTENTS for (s, d, sl, fi) in train_full[d][:k]]
            arms = {'wnn': WNN(INTENTS, seed, bleach=bleach), 'nb': NB(INTENTS), 't2p': T2P(INTENTS), 'nn1': NN1(INTENTS)}
            for s, d, _, _ in train:
                f = encode(s)
                for m in arms.values(): m.add(f, d)
            frame, rolepos = learn_slots(train)
            row = {'seed': seed, 'k': k, 'bleach': bleach, 'tau': tau}
            for name, m in arms.items():
                # dev-chosen abstention margin for THIS arm (frozen before eval): pick the
                # candidate maximizing dev (correct-or-rightly-abstained) rate
                cands = sorted({round(mg, 4) for s, d, _, _ in dev for _, mg in [predict(m, encode(s), -1e18)]})
                best_t, best_r = -1e18, -1
                for t in cands:
                    ok = n = 0
                    for s, d, _, _ in dev:
                        p, mg = predict(m, encode(s), -1e18)
                        p = p if mg >= t else None
                        ok += (p == d) if d != 'NONE' else (p is None); n += 1
                    if ok / n > best_r: best_r, best_t = ok / n, t
                taus = {'wnn': tau, 'nb': best_t, 't2p': best_t, 'nn1': best_t}[name]
                def pred(s):
                    if name == 'wnn':
                        return predict(m, encode(s), tau)[0]
                    p, mg = predict(m, encode(s), -1e18)
                    return p if mg >= taus else None
                ni = ns_ = nj = nw = na = 0; sf1 = 0.0; perfam = Counter(); perfam_ok = Counter()
                for s, d, gold, _ in ev:
                    p = pred(s)
                    ni += 1
                    fam_ok = p == d
                    if p is None: na += 1
                    if p is not None and fam_ok:
                        ps = extract_slots(s, p, frame, rolepos, NSLOTS[p])
                        gs, qs = set(gold), set(ps or ())
                        inter = len(gs & qs)
                        sf1 += (2 * inter / (len(gs) + len(qs))) if gs or qs else 1.0
                        if ps == tuple(gold): nj += 1
                        ns_ += 1
                wp = sum(1 for s, _, _, _ in ev_wrong if pred(s) is not None)
                wr = len(ev_wrong)
                abst_none = wr - wp
                h2_prec = abst_none / max(abst_none + na, 1)
                h2_rec = abst_none / max(wr, 1)
                fams_seen = {}
                for s, d, gold, fi in ev:
                    fams_seen.setdefault((d, fi), [0, 0])
                    fams_seen[(d, fi)][1] += 1
                    if pred(s) == d: fams_seen[(d, fi)][0] += 1
                row[name] = {'intent': ns_ / ni, 'slotf1': sf1 / max(ns_, 1), 'joint': nj / ni,
                             'abstain_on_eval': na / ni, 'wrong_forced': wp, 'wrong_total': wr,
                             'fam': {f'{d}#{fi}': f'{a}/{b}' for (d, fi), (a, b) in fams_seen.items()},
                             'h2_prec': round(h2_prec, 3), 'h2_rec': round(h2_rec, 3)}
            # majority baseline
            row['majority'] = {'intent': 1.0 / len(INTENTS)}
            # designed-frame router contrast
            ok = 0
            KIND2INT = {'observed': 'teach_attr', 'compound_stored': 'teach_attr', 'attr_answer': 'ask_attr',
                        'retracted': 'retract_attr', 'nothing_to_retract': 'retract_attr', 'isa_stored': 'teach_isa',
                        'isa_yesno': 'is_a_q', 'naming': 'name_skill', 'revision_opened': 'name_skill',
                        'example': 'give_example', 'confirmation_question': 'confirm_answer'}
            for s, d, gold, _ in ev:
                r = H.HSML(seed=seed).hear(s)
                ok += KIND2INT.get(r.get('kind'), 'NONE') == d
            row['frames'] = {'intent': ok / len(ev)}
            all_res.append(row)
            print(json.dumps(row, ensure_ascii=False))
            if k == 8:
                winner = max(ARMS, key=lambda a: row[a]['intent'])
                fresh = {'wnn': lambda: WNN(INTENTS, seed, bleach=bleach), 'nb': lambda: NB(INTENTS),
                         't2p': lambda: T2P(INTENTS), 'nn1': lambda: NN1(INTENTS)}[winner]
                conf_src = arms[winner]
                margins = sorted(round(mg, 4) for s2, d2, _, _ in dev if d2 != 'NONE'
                                 for _, mg in [predict(conf_src, encode(s2), -1e18)])
                conf_t = margins[len(margins) // 4] if margins else 0.0
                # retention/drift: teach intents SEQUENTIALLY (dialogue teach-once order);
                # snapshot each intent's eval accuracy right after it was taught, then final
                m2 = fresh()
                snap = {}
                for d in INTENTS:
                    for s2, d2, _, _ in [x for x in train if x[1] == d]: m2.add(encode(s2), d2)
                    items = [(s2, g) for s2, d2, g, _ in ev if d2 == d]
                    snap[d] = sum(predict(m2, encode(s2), -1e18)[0] == d for s2, g in items) / max(len(items), 1)
                final_int = {}
                for d in INTENTS:
                    items = [(s2, g) for s2, d2, g, _ in ev if d2 == d]
                    final_int[d] = sum(predict(m2, encode(s2), -1e18)[0] == d for s2, g in items) / max(len(items), 1)
                drift = {d: round(snap[d] - final_int[d], 3) for d in INTENTS}
                # confirmation retention (PRE-correction): low-margin or abstained -> confirm with gold -> re-predict
                conf_items = [(s2, d2) for s2, d2, _, _ in ev
                              if predict(m2, encode(s2), -1e18)[1] < conf_t]
                conf_ok = 0
                for s2, d2 in conf_items:
                    m2.add(encode(s2), d2)
                    conf_ok += predict(m2, encode(s2), -1e18)[0] == d2
                # end-to-end hsml semantics (H4, PRE-correction state minus confirmation adds:
                # rebuild to the pure post-training state for the honest H4 number)
                m3 = fresh()
                for s2, d2, _, _ in train: m3.add(encode(s2), d2)
                e2e = Counter()
                for s2, d2, gold, _ in ev:
                    p, mg = predict(m3, encode(s2), -1e18)
                    if p is None: e2e['abstain'] += 1; continue
                    if mg < conf_t: e2e['confirmation'] += 1; continue  # ask first, never write unconfirmed
                    ps = extract_slots(s2, p, frame, rolepos, NSLOTS[p])
                    if ps is None: e2e['abstain'] += 1; continue
                    gr = H.HSML(seed=seed).hear(GLUE[d2](tuple(gold)))
                    pr = H.HSML(seed=seed).hear(GLUE[p](ps))
                    if gr.get('kind') == pr.get('kind') and gr.get('text') == pr.get('text'):
                        e2e['correct'] += 1
                    elif pr.get('kind') == 'abstain': e2e['abstain'] += 1
                    else: e2e['wrong_exec'] += 1
                # correction H3: one gold correction per misclassified eval item
                mis = [(s2, d2) for s2, d2, _, _ in ev if predict(m3, encode(s2), -1e18)[0] != d2]
                for s2, d2 in mis: m3.add(encode(s2), d2)
                rec = sum(predict(m3, encode(s2), -1e18)[0] == d2 for s2, d2 in mis) / max(len(mis), 1)
                corrected_intents = {d2 for _, d2 in mis}
                degr, impr, n_oth = 0.0, 0.0, 0
                for d in INTENTS:
                    if d in corrected_intents: continue
                    items = [(s2, g) for s2, d2, g, _ in ev if d2 == d]
                    after = sum(predict(m3, encode(s2), -1e18)[0] == d for s2, g in items) / max(len(items), 1)
                    degr += max(0.0, final_int[d] - after); impr += max(0.0, after - final_int[d]); n_oth += 1
                print('PHASE2 ' + json.dumps({'seed': seed, 'winner': winner, 'conf_t': conf_t,
                      'drift_per_intent': drift, 'drift_mean': round(sum(drift.values()) / len(drift), 3),
                      'e2e': dict(e2e), 'e2e_total': len(ev),
                      'confirm_routed': len(conf_items), 'confirm_retained': conf_ok,
                      'corrected': len(mis), 'recovery': round(rec, 3),
                      'collateral_degr_mean': round(degr / max(n_oth, 1), 4),
                      'collateral_impr_mean': round(impr / max(n_oth, 1), 4)}, ensure_ascii=False))
    # aggregate
    agg = {}
    for name in ARMS + ['frames', 'majority']:
        agg[name] = {}
        for k in Ks:
            rows = [r for r in all_res if r['k'] == k]
            agg[name][k] = {'intent': sum(r[name]['intent'] for r in rows) / len(rows)}
            if name in ARMS:
                agg[name][k]['slotf1'] = sum(r[name]['slotf1'] for r in rows) / len(rows)
                agg[name][k]['joint'] = sum(r[name]['joint'] for r in rows) / len(rows)
                agg[name][k]['wrong_forced'] = sum(r[name]['wrong_forced'] for r in rows)
    print('AGG ' + json.dumps(agg, ensure_ascii=False))
    # shuffled-label sanity control (seed 99, k=8)
    rng = random.Random(99)
    train = [(s, d, sl, fi) for d in INTENTS for (s, d, sl, fi) in gen(rng, d, FAM[d], VOCAB[d], 8)]
    labels = [d for _, d, _, _ in train]; rng.shuffle(labels)
    m = NB(INTENTS)
    for (s, _, _, _), d in zip(train, labels): m.add(encode(s), d)
    ev = [it for d in INTENTS for it in gen(rng, d, EVAL_FAM[d], EVAL_VOCAB[d], 8)]
    acc = sum(predict(m, encode(s), -1e18)[0] == d for s, d, _, _ in ev) / len(ev)
    print('SHUFFLED_CONTROL ' + json.dumps({'nb_intent': acc, 'chance': 1.0 / len(INTENTS)}, ensure_ascii=False))
    print('PEAK_RSS_MB %.1f' % (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024))

if __name__ == '__main__':
    main()
