"""B-589: Thai segmentation probe - supplied longest-match + authored lexicon
on DE-SPACED protocol utterances + authored ordinary sentences.
Usage: python3 b589.py
"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NEW_EVAL_FAM
from b565 import FRESH3_FAM, EVAL_VOCAB2
from b570 import Watchdog, BUDGET, TIMEOUT_S

LEX = set('''มิโล แมว หมา นก ปลา หาง ปีก ขา ตา หู เป็น มี ไหม คือ คืออะไร ของ ไม่มี
เลย นะ นั้น ประเภทหนึ่ง หรือเปล่า บวก ลบ คูณ หาร ถ้า ตอบ ตอบว่า อยากรู้ ดู บอก
หน่อย ไม่จริง นับเป็น ใช่ สมมติ ให้ เหยี่ยว กวาง แพะ เกล็ด เขา งา สัตว์เลี้ยง
แมลง ม้า ควาย เป็ด ขน จงอย่าง ปาก สัตว์ป่า นกน้ำ แบ่ง ลด สิบ แปด เก้า เจ็ด หนึ่ง
สอง สาม สี่ ห้า หก ยี่สิบ ร้อย พัน หมื่น สัตว์ ตัวนี้ ด้วยนะ ช่วยบอกหน่อยว่า ที่จริง
ถือว่าเป็น อยากถามว่า อยากได้ ได้ไหม ลอง แล้ว ขอ ขอตอบ ไป มัน อยู่นะ รู้ไหม หรอก
ใช่ไหม ไปเลย สวัสดี วันนี้ อากาศ ดี มาก ราคา เท่าไหร่ กัน ชื่อ กิน วิธี สอน'''.split())

def segment(text, lex):
    """Longest-match left-to-right; unknown chars grouped."""
    out = []; i = 0; n = len(text)
    while i < n:
        best = None
        for L in range(min(12, n - i), 0, -1):
            w = text[i:i+L]
            if w in lex: best = w; break
        if best: out.append(best); i += len(best)
        else:
            j = i + 1
            while j < n and not any(text[j:j+L] in lex for L in range(min(12, n-j), 0, -1)):
                j += 1
            out.append('<UNK:%s>' % text[i:j]); i = j
    return out

AUTHORED = [  # (despaced ordinary Thai, note)
    ('มิโลเป็นแมว', 'ordinary, in-lexicon'),
    ('วันนี้อากาศดีมาก', 'ordinary sentence'),
    ('ตาเล็กมองเหยี่ยว', 'ambiguity: ตา/เล็ก vs ตาเล็ก; เล็ก not in lexicon'),
    ('เขามีงาใหญ่', 'ambiguity: เขา(pronoun) vs เขา(horn) - classic Thai ambiguity'),
    ('แมวตัวนี้ชื่อมิโลนะ', 'mixed known/unknown'),
]

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    sets = {}
    sets['train_family'] = [(s, d) for d in B.INTENTS for (s, d, g, fi) in B.gen(rng, d, B.FAM[d], B.VOCAB[d], 8)]
    sets['c22_fresh'] = [(s, d) for d in B.INTENTS for (s, d, g, fi) in B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8)]
    for name, items in sets.items():
        exact = unk = 0
        fails = []
        for s, d in items:
            despaced = s.replace(' ', '')
            toks = segment(despaced, LEX)
            if toks == s.split(): exact += 1
            else:
                fails.append((s, toks))
                if any(t.startswith('<UNK:') for t in toks): unk += 1
        print('ROW ' + json.dumps({'set': name, 'n': len(items), 'exact_recovery': exact,
            'with_unknown': unk, 'fail_examples': fails[:3]}, ensure_ascii=False))
    for text, note in AUTHORED:
        print('AUTH ' + json.dumps({'text': text, 'segmented': segment(text, LEX), 'note': note}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1), 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
