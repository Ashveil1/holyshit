"""B-597: vocabulary bootstrapping probe. Usage: python3 b597.py"""
import json, time, re
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET
from b574 import pick_tau_precision
from b592 import HSMLChat
from b589 import LEX, segment

UNK = re.compile(r'<UNK:([^>]+)>')

class ChatVocab(HSMLChat):
    def __init__(self, *a):
        super().__init__(*a)
        self.lex = set(LEX); self.vocab_learned = []
    def turn_raw(self, raw, gold_intent, gold_slots, scripted=None, teacher_yes=True):
        seg = ' '.join(segment(raw, self.lex))
        unks = UNK.findall(seg)
        asked_vocab = False
        if unks:
            # one clarification per turn: ask about the first unknown word
            self.q += 1; asked_vocab = True
            if teacher_yes:
                self.corr += 1  # teacher supplies the word (a correction-cost interaction)
                w = unks[0]
                self.lex.add(w); self.vocab_learned.append(w)
                seg = seg.replace('<UNK:%s>' % w, w)
                # re-segment remainder in case the UNK hid boundaries
                seg = ' '.join(segment(seg.replace(' ', ''), self.lex))
            else:
                return 'honest_engaged', {'vocab_asked': True, 'seg': seg}
        cls, meta = self.turn(seg, gold_intent, gold_slots, scripted)
        meta['vocab_asked'] = asked_vocab; meta['seg'] = seg
        return cls, meta

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    chat = ChatVocab(m, tau_hi, 1.0, extract)
    rows = []
    # (raw, gold, slots, scripted, expect, note)
    cases = [
        ('ช้างเป็นสัตว์', 'teach_isa', ('ช้าง', 'สัตว์'), ('teach_isa', ('ช้าง', 'สัตว์')), 'teach_ok', 'unknown word, teacher confirms'),
        ('ช้างมีงา', 'teach_attr', ('ช้าง', 'งา'), ('teach_attr', ('ช้าง', 'งา')), 'teach_ok', 'SAME word, new predicate: no vocab question expected'),
        ('ช้างเป็นสัตว์ไหม', 'is_a_q', ('ช้าง', 'สัตว์'), None, 'inference_ok', 'SAME word, inference question: no vocab question, answered from taught facts'),
        ('เสือเป็นสัตว์', 'teach_isa', ('เสือ', 'สัตว์'), ('teach_isa', ('เสือ', 'สัตว์')), 'teach_ok', 'NEW unknown word: one vocab question'),
        ('มิโลเป็นแมว', 'teach_isa', ('มิโล', 'แมว'), None, 'teach_ok', 'control: all in-lexicon'),
    ]
    q_before = 0
    for raw, gi, gs, scripted, expect, note in cases:
        q0 = chat.q
        cls, meta = chat.turn_raw(raw, gi, gs, scripted)
        wrong = cls in ('teach_ok', 'answer_ok', 'inference_ok') and gi is None
        rows.append({'raw': raw, 'seg': meta['seg'][:40], 'cls': cls, 'expect': expect,
                     'vocab_asked': meta['vocab_asked'], 'questions_this_turn': chat.q - q0,
                     'ok': cls == expect and not wrong, 'note': note})
    for r in rows: print('CASE ' + json.dumps(r, ensure_ascii=False))
    snap_ok = 'ช้าง' in chat.lex and 'ช้าง' in chat.vocab_learned
    print('SUMMARY ' + json.dumps({'ok': sum(r['ok'] for r in rows), 'cases': len(rows),
        'questions_total': chat.q, 'vocab_learned': chat.vocab_learned,
        'lexicon_growth_recorded': snap_ok, 'fabricated': chat.fabricated}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
    print('DONE')
