"""P31 (baby7.py): turn-taking dialogue with contingent feedback (pre-registered with owner).
Episode: caregiver prompt (scene-prompt or greeting) + END token -> baby decides to speak (reward-shaped)
and picks a word evoked by the PRESENT tokens (association) -> caregiver praise/correction.
Reward modulates word<->present-token association (praise strengthens, correction weakens) and
speak-propensity by context (END vs no-END). T1 >=.9/<=.2; T2 >=.8; T3 day1->day5 >=+.2;
controls: NO-FEEDBACK (random reward), SHUFFLED-PROMPT (prompt scene != visible scene)."""
import random, json, sys
from collections import defaultdict
from baby5 import WorldC, Baby5, load_llm_pools, WE, WA, WL, TOK, ENT, ACT, VALID
ENDT = 'ZEND'   # end-of-turn prosody token (perceptual, not a slot label)
P_SCENE = ['เห็น อะไร ดูสิ', 'นั่น อะไร จ๊ะ', 'มอง สิ ลูก']
P_GREET = ['สวัสดี ลูก', 'หวัดดี จ๊ะ ลูก']
ECHO = 'สวัสดี'
class Baby7(Baby5):
    def __init__(s):
        super().__init__()
        s.pspeak = {'end': 0.5, 'noend': 0.5}
    def grounded(s, w):
        av = s.assoc.get(w, {})
        if not av: return False
        top2 = sorted(av.values(), reverse=True)[:2]
        return len(top2) == 2 and top2[0] > 0 and top2[0] >= 1.5 * max(top2[1], 0.01)
    def produce(s, present, rng, greet=False):
        if greet: return ECHO if ECHO in s.assoc else None
        cands = []
        for w in s.assoc:
            if not s.grounded(w): continue  # only confidently-grounded words are sayable
            av = s.assoc[w]
            evoked = sum(av.get(t, 0.0) for t in present)
            if evoked > 0: cands.append((w, evoked))
        if not cands: return None
        cands.sort(key=lambda c: -c[1])
        return rng.choice(cands[:3])[0]
def run_d(seed, f, pool_a, pool_b, covered, days=5, eps_per_day=100, feedback=True, shuffled=False):
    rng = random.Random(4000 + seed); w = WorldC(rng, covered); b = Baby7()
    day_approp = defaultdict(list); transcripts = []
    for day in range(days):
        for ep in range(eps_per_day):
            sc = w.scene(); pres = set(w.tokens(sc))
            for _ in range(rng.choice((1, 2))):
                b.hear(pool_a(rng, sc) if rng.random() < f else pool_b(rng), pres)
            greet = rng.random() < 0.3
            prompt = rng.choice(P_GREET if greet else P_SCENE)
            names = {WE[sc[0]], WA[sc[1]], WL[sc[2]]}
            if shuffled:
                sc_h = w.scene(); names_fb = {WE[sc_h[0]], WA[sc_h[1]], WL[sc_h[2]]}  # caregiver attends a HIDDEN scene
            else:
                names_fb = names
            b.hear(prompt.split(), pres)  # END token is a timing cue, not a vocab word
            # no-END probe context (caregiver hasn't finished): baby should learn to stay silent
            if rng.random() < 0.25 and b.decide_speak_probe(False, rng):
                if feedback: b.pspeak['noend'] = max(0.01, b.pspeak['noend'] - 0.05)
            if not b.decide_speak_probe(True, rng): continue
            word = b.produce(pres, rng, greet=greet)
            if word is None: continue
            if greet:
                good = (word == ECHO)
            else:
                good = word in names_fb  # competent-caregiver criterion: conventional name of an attended thing
            day_approp[day].append(1.0 if good else 0.0)
            reward = 1.0 if good else -1.0
            if not feedback: reward = rng.choice((1.0, -1.0))
            # reward-modulated plasticity: produced word <-> present tokens
            for t in pres: b.assoc[word][t] += 0.3 * reward
            if feedback: b.pspeak['end'] = min(0.99, max(0.01, b.pspeak['end'] + 0.05 * reward))
            fb = ('ใช่! ' + word) if good else ('ไม่ใช่ นั่นคือ ' + WE[sc[0]] if not greet else '...')
            b.hear(fb.split(), pres)
            if day == days - 1 and len(transcripts) < 3:
                transcripts.append({'prompt': prompt, 'baby': word, 'fb': fb, 'good': good})
    ok = 0; n = 100
    prng = random.Random(99)
    for _ in range(n):
        sc = w.scene(); pres = set(w.tokens(sc))
        word = b.produce(pres, prng)
        if word:
            ok += word in {WE[sc[0]], WA[sc[1]], WL[sc[2]]}
    echo_ok = sum(1 for _ in range(20) if b.produce(set(), prng, greet=True) == ECHO)
    d1 = sum(day_approp[0]) / max(1, len(day_approp[0]))
    d5 = sum(day_approp[days - 1]) / max(1, len(day_approp[days - 1]))
    return dict(t1_end=round(b.pspeak['end'], 2), t1_noend=round(b.pspeak['noend'], 2),
                t2=ok / n, echo=echo_ok, d1=round(d1, 2), d5=round(d5, 2), delta=round(d5 - d1, 2), tr=transcripts)
Baby7.decide_speak_probe = lambda s, end, rng: rng.random() < s.pspeak['end' if end else 'noend']
if __name__ == '__main__':
    pa, pb, covered = load_llm_pools(sys.argv[1])
    for mode, fb, sh in (('NORMAL', True, False), ('NO-FEEDBACK', False, False), ('SHUFFLED-PROMPT', True, True)):
        for f in (1.0, 0.2):
            for seed in range(3):
                r = run_d(seed, f, pa, pb, covered, feedback=fb, shuffled=sh)
                print(f"{mode} f={f} seed{seed}: T1 end/noend={r['t1_end']}/{r['t1_noend']} T2={r['t2']:.2f} echo={r['echo']}/20 d1->d5={r['d1']}->{r['d5']} (+{r['delta']}) tr={json.dumps(r['tr'][:1], ensure_ascii=False)[:150]}", flush=True)
