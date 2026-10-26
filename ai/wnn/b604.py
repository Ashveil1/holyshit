"""B-604: familiar-word slot assignment fallback, gold-supervised.
Pre-registered in LEDGER.md B-604. Usage: python3 b604.py
"""
import json, time
from collections import Counter, defaultdict
import b562 as B
from b562_diag import build
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET

def learn_gold_stats(train):
    """Train-only, gold-supervised: per-intent frame words (frequent AND
    never a gold filler), global filler set, and per-(intent,slot) anchor
    offset stats."""
    by = defaultdict(list)
    fillers = set()
    vocab = set()
    for s, d, slots, _ in train:
        by[d].append((s, slots))
        fillers.update(slots)
        vocab.update(s.split())
    frame = {}
    for d, ss in by.items():
        c = Counter(w for s, _ in ss for w in set(s.split()))
        slot_words = Counter(w for _, slots in ss for w in slots)
        frame[d] = {w for w, n in c.items() if n >= max(1, 0.5 * len(ss)) and slot_words[w] == 0}
    return frame, fillers, vocab

def slot_offsets(train, anchor):
    """slots_off[d][k] = Counter of gold-slot-k token offsets vs anchor."""
    off = defaultdict(lambda: defaultdict(Counter))
    for s, d, slots, _ in train:
        toks = s.split()
        if anchor[d] not in toks: continue
        ap = toks.index(anchor[d])
        for k, w in enumerate(slots):
            if w in toks:
                off[d][k][toks.index(w) - ap] += 1
    return off

def select_std(s, d, functionish, anchor, offstat, frame, nslots, fillers=None, vocab=None):
    """Standard S4 selection PLUS per-intent frame-word exclusion (B-604
    fix: grammar words like ไหม/คืออะไร are single-intent so the
    cross-intent functionish filter misses them)."""
    toks = s.split()
    ap = toks.index(anchor[d]) if anchor[d] in toks else None
    fr = set().union(*frame.values()) if frame else set()
    cands = []
    for i, w in enumerate(toks):
        if w in functionish or w == anchor[d] or w in fr: continue
        if vocab is not None and w in vocab and w not in fillers: continue
        off = (i - ap) if ap is not None else None
        lik = offstat[d].get(off, 0) if off is not None else 0
        cands.append((lik, i, w))
    cands.sort(key=lambda t: (-t[0], t[1]))
    return [w for _, _, w in cands[:nslots]], toks

def extract_fb(s, d, functionish, anchor, offstat, rolepos, frame, fillers, soff, nslots, vocab=None):
    picked, toks = select_std(s, d, functionish, anchor, offstat, frame, nslots, fillers, vocab)
    if len(picked) >= nslots:
        return assign_a0(picked, toks, nslots), 'standard'
    if d not in frame: return None, 'fallback_failed'
    ap = toks.index(anchor[d]) if anchor[d] in toks else None
    cands = []
    for i, w in enumerate(toks):
        if w in frame[d] or w == anchor[d]: continue
        if w not in fillers and w in functionish: continue   # seen-but-never-filler = grammar
        off = (i - ap) if ap is not None else None
        cands.append((i, w, off))
    if len(cands) < nslots: return None, 'fallback_failed'
    assigned = [None] * nslots; used = set()
    # greedy: best (slot k, candidate) pairs by gold offset stats
    pairs = []
    for i, w, off in cands:
        for k in range(nslots):
            pairs.append((soff[d][k].get(off, 0), k, i, w))
    pairs.sort(key=lambda t: -t[0])
    for cnt, k, i, w in pairs:
        if assigned[k] is None and w not in used:
            assigned[k] = w; used.add(w)
    left = [w for i, w, off in cands if w not in used]
    li = 0
    for k in range(nslots):
        if assigned[k] is None:
            assigned[k] = left[li] if li < len(left) else None; li += 1
    if any(x is None for x in assigned): return None, 'fallback_failed'
    return tuple(assigned), 'fallback'

GRID = [('แมว เป็น นก', 'teach_isa', ('แมว', 'นก')),
        ('แมว เป็น สัตว์', 'teach_isa', ('แมว', 'สัตว์')),
        ('แมว มี หาง', 'teach_attr', ('แมว', 'หาง')),
        ('มิโล เป็น แมว', 'is_a_q', ('มิโล', 'แมว')),
        ('มิโล เป็น แมว ไหม', 'is_a_q', ('มิโล', 'แมว')),
        ('แมว เป็น สัตว์ ไหม', 'is_a_q', ('แมว', 'สัตว์')),
        ('แมว มี หาง ไหม', 'teach_attr', ('แมว', 'หาง')),
        ('หาง ของ แมว คืออะไร', 'ask_attr', ('แมว', 'หาง')),
        ('แมว ไม่มี ปีก', 'retract_attr', ('แมว', 'ปีก')),
        ('เหยี่ยว เป็น นก', 'teach_isa', ('เหยี่ยว', 'นก')),
        ('หมู มี งา', 'teach_attr', ('หมู', 'งา')),
        ('นก มี ปีก ไหม', 'teach_attr', ('นก', 'ปีก')),
        ('วันนี้ อากาศ ดี มาก', 'ask_attr', None),
        ('สวัสดี', 'name_skill', None)]

if __name__ == '__main__' and '--heldout' not in __import__('sys').argv:
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    frame, fillers, vocab = learn_gold_stats(train)
    soff = slot_offsets(train, anchor0)
    ok = 0; swaps = 0
    for s, d, want in GRID:
        got, how = extract_fb(s, d, fn0, anchor0, offstat0, rolepos0, frame, fillers, soff, B.NSLOTS[d], vocab)
        if want is None:
            good = got is None
        else:
            good = got == want
            swaps += got is not None and set(got) == set(want) and got != want
        ok += good
        print('GRID ' + json.dumps({'s': s, 'intent': d, 'want': want, 'got': got, 'how': how, 'ok': good}, ensure_ascii=False))
    # G3: fallback inert on frozen protocol eval (intents in NSLOTS only)
    tot = fired = identical = 0
    for s, d, g, fi in (ev[:200] + ev_wrong[:50]):
        if d not in B.NSLOTS: continue
        tot += 1
        old_std, _ = _select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d])
        old_a = assign_a0(old_std, s.split(), B.NSLOTS[d])
        fb, how = extract_fb(s, d, fn0, anchor0, offstat0, rolepos0, frame, fillers, soff, B.NSLOTS[d], vocab)
        gold = tuple(g) if g else None
        if fb == old_a: identical += 1
        else: print('G3-DELTA ' + json.dumps({'s': s, 'd': d, 'old': old_a, 'new': fb, 'gold': gold}, ensure_ascii=False))
        if how != 'standard': fired += 1
    print('G3 ' + json.dumps({'eval_items': tot, 'standard_path': tot - fired,
        'outputs_identical_to_old': identical, 'fallback_fired': fired}))
    print('SUMMARY ' + json.dumps({'grid_ok': ok, 'grid_n': len(GRID), 'role_swaps': swaps}))
    watchdog.stop()
    print('RES ' + json.dumps({'mb': round(watchdog.peak/1e6,1), 's': round(time.time()-t0,1)}))

# ---- B-604 audit: matched pre/post contrast on HELD-OUT unfamiliar
# compositions (authored for evaluation only; never added to runtime) ----
HELDOUT = [('ควาย มี เขา', 'teach_attr', ('ควาย', 'เขา')),
           ('เขา ของ ควาย คืออะไร', 'ask_attr', ('เขา', 'ควาย')),  # surface-order convention
           ('เป็ด เป็น นก ไหม', 'is_a_q', ('เป็ด', 'นก')),
           ('เสือ มี ขน', 'teach_attr', ('เสือ', 'ขน')),
           ('สัตว์ป่า เป็น สัตว์', 'teach_isa', ('สัตว์ป่า', 'สัตว์')),
           ('นกน้ำ มี ปีก ไหม', 'teach_attr', ('นกน้ำ', 'ปีก')),
           ('เกล็ด ของ ปลา คืออะไร', 'ask_attr', ('เกล็ด', 'ปลา')),
           ('ม้า ไม่มี เขา', 'retract_attr', ('ม้า', 'เขา'))]

def heldout_contrast():
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    frame, fillers, vocab = learn_gold_stats(train)
    soff = slot_offsets(train, anchor0)
    pre = post = 0
    for s, d, want in HELDOUT:
        picked, toks = _select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d])
        got_pre = assign_a0(picked, toks, B.NSLOTS[d])
        got_post, how = extract_fb(s, d, fn0, anchor0, offstat0, rolepos0, frame, fillers, soff, B.NSLOTS[d], vocab)
        pre += got_pre == want; post += got_post == want
        print('HELDOUT ' + json.dumps({'s': s, 'want': want, 'pre': got_pre, 'post': got_post, 'how': how}, ensure_ascii=False))
    print('CONTRAST ' + json.dumps({'heldout_n': len(HELDOUT), 'pre_standard_only': pre, 'post_with_fallback': post}))

if __name__ == '__main__' and '--heldout' in __import__('sys').argv:
    heldout_contrast()
