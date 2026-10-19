"""P15: learn natural-language commands (English + Thai) -> library program, from (sentence, answer) pairs only.
Nobody tells the learner which operation a sentence means. For each training pair it finds which (op, argument-order)
hypotheses reproduce the answer, spreads credit over them, and learns word / char-n-gram -> hypothesis weights
(naive Bayes with soft counts, so ambiguity from coinciding numbers is resolved across examples).
GIVEN: the skill library (add sub mul div mod power gcd max min isprime fact sumto, as functions; learned in P7-P14),
  the hypothesis space = {op} x {forward, reverse argument order} (variadic ops fold over all numbers),
  digit extraction by regex, feature extractors (whitespace tokens or char n-grams), the sentence templates (the data).
LEARNED: which words/n-grams mean which op and which order.
python3 text2prog.py [seed]"""
import re, sys, random, math, itertools
from collections import defaultdict
sys.setrecursionlimit(10000)
isp = lambda n: int(n > 1 and all(n % d for d in range(2, int(n ** .5) + 1)))
OPS = {
 'add': lambda *v: sum(v), 'sub': lambda a, b: a - b, 'mul': lambda *v: math.prod(v), 'div': lambda a, b: a // b,
 'mod': lambda a, b: a % b, 'power': lambda a, b: a ** b, 'gcd': lambda *v: math.gcd(*v),
 'max': lambda *v: max(v), 'min': lambda *v: min(v), 'isprime': lambda a: isp(a),
 'fact': lambda a: math.factorial(a), 'sumto': lambda a: a * (a + 1) // 2}
UNARY = {'isprime', 'fact', 'sumto'}
HYP = [(o, d) for o in OPS for d in ('f', 'r') if not (o in UNARY and d == 'r')]
# templates: (train, new_frames, new_words).  {a}{b}{c} are numbers; Thai written with spaces between words.
T = {
 'add': (["add {a} and {b}", "what is {a} plus {b}", "บวก {a} กับ {b}", "{a} บวก {b} เท่ากับเท่าไหร่", "add {a} {b} and {c}"],
         ["please add {b} to {a}", "{a} plus {b} please", "ช่วย บวก {a} กับ {b} หน่อย", "แล้ว {a} บวก {b} ล่ะ"], ["total of {a} and {b}", "รวม {a} กับ {b}"]),
 'sub': (["{a} minus {b}", "subtract {b} from {a}", "{a} ลบ {b}", "ลบ {b} ออกจาก {a}"],
         ["what is {a} minus {b} please", "please subtract {b} from {a}", "ช่วย ลบ {b} ออกจาก {a}", "{a} ลบ {b} ได้เท่าไหร่"], ["take {b} away from {a}", "{a} less {b}", "หัก {b} จาก {a}"]),
 'mul': (["multiply {a} by {b}", "{a} times {b}", "คูณ {a} กับ {b}", "{a} คูณ {b}"],
         ["what is {a} times {b}", "please multiply {a} by {b}", "ช่วย คูณ {a} กับ {b}", "{a} คูณ {b} ได้เท่าไหร่"], ["product of {a} and {b}", "ผลคูณ ของ {a} กับ {b}"]),
 'div': (["divide {a} by {b}", "{a} divided by {b}", "หาร {a} ด้วย {b}", "{a} หาร {b}"],
         ["what is {a} divided by {b}", "please divide {a} by {b}", "ช่วย หาร {a} ด้วย {b}", "{a} หาร {b} ได้เท่าไหร่"], ["how many times does {b} go into {a}", "{b} ใส่ได้กี่ครั้งใน {a}"]),
 'mod': (["remainder of {a} divided by {b}", "{a} mod {b}", "เศษ ของ {a} หาร {b}", "{a} มอด {b}"],
         ["what is the remainder of {a} divided by {b}", "please {a} mod {b}", "ช่วย หา เศษ ของ {a} หาร {b}", "{a} มอด {b} เท่าไหร่"], ["what is left over when {a} is split by {b}", "{a} เหลือเศษ เท่าไหร่ เมื่อ หาร {b}"]),
 'power': (["{a} to the power of {b}", "raise {a} to {b}", "{a} ยกกำลัง {b}", "ยกกำลัง {a} ด้วย {b}"],
         ["what is {a} to the power of {b}", "please raise {a} to {b}", "ช่วย ยกกำลัง {a} ด้วย {b}", "{a} ยกกำลัง {b} เท่าไหร่"], ["{a} raised {b} times by itself", "{a} กำลัง {b}"]),
 'gcd': (["gcd of {a} and {b}", "ห.ร.ม. ของ {a} กับ {b}", "gcd {a} {b}", "หา ห.ร.ม. {a} {b}"],
         ["what is the gcd of {a} and {b}", "please gcd of {b} and {a}", "ช่วย หา ห.ร.ม. ของ {a} กับ {b}", "ห.ร.ม. {a} กับ {b} เท่าไหร่"], ["greatest common divisor of {a} and {b}", "ตัวหารร่วมมาก ของ {a} กับ {b}"]),
 'max': (["largest of {a} {b} {c}", "maximum of {a} and {b}", "มากที่สุด ใน {a} {b} {c}", "ค่าสูงสุด {a} {b}"],
         ["what is the largest of {a} {b} {c}", "please maximum of {a} and {b}", "ช่วย หา มากที่สุด ใน {a} {b} {c}", "ใน {a} {b} {c} อะไร มากที่สุด"], ["which is bigger {a} or {b}", "อันไหน ใหญ่กว่า {a} หรือ {b}"]),
 'min': (["smallest of {a} {b} {c}", "minimum of {a} and {b}", "น้อยที่สุด ใน {a} {b} {c}", "ค่าต่ำสุด {a} {b}"],
         ["what is the smallest of {a} {b} {c}", "please minimum of {a} and {b}", "ช่วย หา น้อยที่สุด ใน {a} {b} {c}", "ใน {a} {b} {c} อะไร น้อยที่สุด"], ["which is smaller {a} or {b}", "อันไหน เล็กกว่า {a} หรือ {b}"]),
 'isprime': (["is {a} prime", "is {a} a prime number", "{a} เป็น จำนวนเฉพาะ ไหม", "{a} เป็น จำนวนเฉพาะ หรือเปล่า"],
         ["please check if {a} is prime", "tell me is {a} a prime", "ช่วย ดู ว่า {a} เป็น จำนวนเฉพาะ ไหม", "{a} คือ จำนวนเฉพาะ ใช่ไหม"], ["can {a} only be split by 1 and itself", "{a} หารลงตัว แค่ กับ ตัวเอง ไหม"]),
 'fact': (["factorial of {a}", "{a} factorial", "แฟกทอเรียล ของ {a}", "{a} แฟกทอเรียล"],
         ["what is the factorial of {a}", "please {a} factorial", "ช่วย หา แฟกทอเรียล ของ {a}", "แฟกทอเรียล {a} เท่าไหร่"], ["multiply every number from {a} down to one", "คูณ ทุกตัว ตั้งแต่ {a} ลง ถึง หนึ่ง"]),
 'sumto': (["sum up to {a}", "add all numbers up to {a}", "ผลรวม ถึง {a}", "บวก ทุกตัว ถึง {a}"],
         ["what is the sum up to {a}", "please add all numbers up to {a}", "ช่วย หา ผลรวม ถึง {a}", "ผลรวม ถึง {a} เท่าไหร่"], ["running total until {a}", "รวม ไป เรื่อยๆ จน ถึง {a}"]),
}
def draw(op, rng, big):
    lo, hi = (31, 99) if big else (2, 30)
    if op == 'power': a, b = rng.randrange(2, 10), rng.randrange(2, 5); return a, b, rng.randrange(2, 10)
    if op == 'fact': a = rng.randrange(2, 9 if not big else 11); return a, 0, 0
    if op == 'sumto': a = rng.randrange(3, 40 if not big else 150); return a, 0, 0
    if op == 'isprime': a = rng.randrange(lo, hi); return a, 0, 0
    a, b, c = rng.randrange(lo, hi), rng.randrange(lo, hi), rng.randrange(lo, hi)
    if op == 'sub' and a < b: a, b = b, a
    if op in ('div', 'mod'): b = rng.randrange(2, 12)
    return a, b, c
def numbers_of(text): return [int(x) for x in re.findall(r'\d+', text)]
def make(op, tmpl, rng, big=False):
    a, b, c = draw(op, rng, big)
    text = tmpl.format(a=a, b=b, c=c)
    nums = numbers_of(text)
    # ground-truth answer: the operation is applied with the numbers in the order the template defines
    if op == 'sub': ans = a - b
    elif op == 'div': ans = a // b
    elif op == 'mod': ans = a % b
    elif op == 'power': ans = a ** b
    elif op in UNARY: ans = OPS[op](a)
    else: ans = OPS[op](*nums)
    # the {b} {a} reverse-order sentences ("subtract {b} from {a}") keep the true meaning a-b
    if op in ('gcd',) and 'of {b} and {a}' in tmpl: ans = math.gcd(a, b)
    return text, int(ans)
def run_hyp(h, nums):
    op, d = h
    v = nums[::-1] if d == 'r' else nums
    f = OPS[op]
    try:
        if op in UNARY: return int(f(v[0]))
        if op in ('sub', 'div', 'mod', 'power'): return int(f(v[0], v[1]))
        return int(f(*v))
    except Exception: return None
def feats(text, kind):
    t = re.sub(r'\d+', ' ', text.lower()); t = ' '.join(t.split())
    if kind == 'tok':
        w = t.split(); return set(w) | set(zip(w, w[1:]))
    if kind == 'tokuni': return set(t.split())
    if kind == 'char': s = ' ' + t + ' '; return {s[i:i + 3] for i in range(len(s) - 2)} | {s[i:i + 2] for i in range(len(s) - 1)}
class Learner:
    def __init__(s, kind='tok', soft=True): s.kind = kind; s.soft = soft; s.cnt = defaultdict(lambda: defaultdict(float)); s.tot = defaultdict(float); s.prior = defaultdict(float)
    def fit(s, data):
        for text, ans in data:
            nums = numbers_of(text); C = [h for h in HYP if run_hyp(h, nums) == ans]
            if not C: continue
            w = 1.0 / len(C) if s.soft else 1.0
            for f in feats(text, s.kind):
                s.tot[f] += w
                for h in C: s.cnt[f][h] += w
            for h in C: s.prior[h] += w
    def predict(s, text):
        fs = [f for f in feats(text, s.kind) if f in s.tot]
        best, bs = None, -1e18
        for h in HYP:
            sc = 0.0
            for f in fs: sc += math.log((s.cnt[f].get(h, 0) + 0.05) / (s.tot[f] + 0.05 * len(HYP)))
            if sc > bs: best, bs = h, sc
        return best, len(fs)
    def answer(s, text):
        h, n = s.predict(text); return run_hyp(h, numbers_of(text)), h, n
def gen_set(rng, which, n, big=False, ops=None):
    out = []
    for _ in range(n):
        op = rng.choice(ops or list(T)); tm = rng.choice(T[op][which]); out.append((op,) + make(op, tm, rng, big))
    return out
def evaluate(L, rows):
    ok = 0; byop = defaultdict(lambda: [0, 0])
    for op, text, ans in rows:
        try: r = L.answer(text)[0]
        except Exception: r = None
        ok += r == ans; byop[op][0] += r == ans; byop[op][1] += 1
    return ok / len(rows), byop
def nospace(text):
    if re.search(r'[\u0e00-\u0e7f]', text): return re.sub(r'\s+', '', text) if False else re.sub(r'(?<=\D) (?=\D)', '', text)
    return text
def fast_map(kind, seed, n_train=300, ks=(0, 1, 2, 4, 8)):
    """for every unseen-synonym template: after k labelled examples using it, accuracy on that template with unseen numbers."""
    res = {k: [] for k in ks}
    for op in T:
        for tm in T[op][2]:
            for k in ks:
                rng = random.Random(seed)
                L = Learner(kind); L.fit([(t, a) for _, t, a in gen_set(rng, 0, n_train)])
                L.fit([make(op, tm, rng) for _ in range(k)])
                r = random.Random(500 + seed); ok = 0
                for _ in range(40):
                    text, ans = make(op, tm, r, big=True)
                    try: ok += L.answer(text)[0] == ans
                    except Exception: pass
                res[k].append(ok / 40)
    return {k: sum(v) / len(v) for k, v in res.items()}
if __name__ == '__main__':
    seeds = range(5); kinds = ('tok', 'char')
    print('hypotheses:', len(HYP), '| templates per op: 4-5 train, 4 new-frame, 2 new-synonym; Thai + English mixed', flush=True)
    for kind in kinds:
        for n in (24, 60, 150, 400):
            sc = defaultdict(list)
            for sd in seeds:
                rng = random.Random(sd)
                L = Learner(kind); L.fit([(t, a) for _, t, a in gen_set(rng, 0, n)])
                r = random.Random(100 + sd)
                for nm, wh in (('numbers', 0), ('frames', 1), ('synonyms', 2)): sc[nm].append(evaluate(L, gen_set(r, wh, 300, big=True))[0])
            print(f'{kind:5s} n={n:4d} ' + ' | '.join(f'{k} {sum(v)/len(v):.2f} [{min(v):.2f}-{max(v):.2f}]' for k, v in sc.items()), flush=True)
    # per-op unseen-frame accuracy (char, n=400, seed 0)
    rng = random.Random(0); L = Learner('char'); L.fit([(t, a) for _, t, a in gen_set(rng, 0, 400)])
    acc, byop = evaluate(L, gen_set(random.Random(100), 1, 600, big=True))
    print('per-op unseen frames (char n=400):', {o: f'{v[0]}/{v[1]}' for o, v in byop.items()})
    # Thai without spaces (char features only; no tokenization at all)
    sc = []
    for sd in seeds:
        rng = random.Random(sd); L = Learner('char'); L.fit([(nospace(t), a) for _, t, a in gen_set(rng, 0, 400)])
        r = random.Random(100 + sd); rows = [(o, nospace(t), a) for o, t, a in gen_set(r, 1, 300, big=True)]
        sc.append(evaluate(L, rows)[0])
    print(f'char n=400 Thai WITHOUT spaces, unseen frames: {sum(sc)/len(sc):.2f} [{min(sc):.2f}-{max(sc):.2f}]', flush=True)
    for kind in kinds:
        fm = [fast_map(kind, sd) for sd in range(3)]
        print(f'fast mapping of unseen synonyms ({kind}), accuracy after k examples:', {k: round(sum(f[k] for f in fm) / 3, 2) for k in fm[0]}, flush=True)
