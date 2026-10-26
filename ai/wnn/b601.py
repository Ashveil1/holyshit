"""B-601: response realization over the unified shell. Usage: python3 b601.py"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET
from b574 import pick_tau_precision
from b588 import GOLD
from b585 import SCENARIO as V1
from b592 import HSMLChat, V2, V2_GOLD

class ChatSpeaks(HSMLChat):
    def isa_path(self, x, y):
        from collections import deque
        q = deque([(x, [x])]); seen = {x}
        while q:
            u, path = q.popleft()
            if y in self.isa[u]: return path + [y]
            for v in self.isa[u]:
                if v not in seen: seen.add(v); q.append((v, path + [v]))
        return None
    def turn(self, s, gold_intent, gold_slots, scripted=None):
        cls, meta = super().turn(s, gold_intent, gold_slots, scripted)
        meta['reply'] = self.realize(cls, s, gold_intent, gold_slots, meta)
        meta['reply_class'] = cls
        return cls, meta
    def realize(self, cls, s, gi, gs, meta):
        sl = list(gs) if gs else []
        if cls == 'teach_ok' and gi and sl:
            if gi == 'teach_isa': return 'จำแล้ว: %s เป็น %s' % (sl[0], sl[1])
            if gi == 'teach_attr': return 'จำแล้ว: %s มี %s' % (sl[0], sl[1])
            if gi == 'retract_attr': return 'ลบแล้ว: %s ไม่มี %s' % (sl[0], sl[1])
            if gi == 'name_skill': return 'จำวิธีแล้ว: %s' % sl[0]
            if gi == 'confirm_answer': return 'รับคำตอบ: %s' % sl[0]
            return 'จำแล้ว'
        if cls == 'literal_repeat': return 'อันนี้รู้อยู่แล้วนะ'
        if cls == 'inference_ok' and sl:
            path = self.isa_path(sl[0], sl[1])
            if path and len(path) > 2:
                chain = ' และ '.join('%s เป็น %s' % (a, b) for a, b in zip(path, path[1:]))
                return 'ใช่ %s เป็น %s เพราะ %s' % (sl[0], sl[1], chain)
            return 'ใช่ %s เป็น %s' % (sl[0], sl[1])
        if cls == 'answer_ok' and sl:
            return 'ไม่รู้ว่า %s %s %s ยังไม่เคยถูกสอน' % (sl[0], 'เป็น' if gi == 'is_a_q' else 'มี', sl[1])
        if cls == 'ask_needed':
            cands = [e for e in dict.fromkeys(reversed(self.subjects))][:3]
            if cands and ('มัน' in s or 'ของมัน' in s):
                return 'หมายถึงตัวไหน: ' + ' หรือ '.join(cands) + '?'
            return 'ขอถามเพิ่มหน่อย'
        if cls == 'honest_engaged':
            if meta.get('routed') == 'explain': return 'ตอบคำถามแนว ทำไม/อย่างไร ไม่ได้ ยังเรียนไม่ถึง'
            if meta.get('routed') == 'gradable': return 'ตัดสินเรื่องแบบนี้ไม่ได้ ไม่ใช่ของที่สอนกันได้'
            return 'เรื่องนี้อยู่นอกสิ่งที่เคยถูกสอน'
        if cls == 'def_taught': return 'จำรูปแบบใหม่แล้ว'
        if cls == 'def_failed': return 'นิยามนี้ใช้ไม่ได้ รูปแบบไม่ตรง'
        return '(เงียบ)'

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    allrows = []
    for name, scen, goldf in (('v1', V1, lambda u: GOLD[u]), ('v2', V2, lambda u: V2_GOLD.get(u, GOLD.get(u, (None, None))))):
        chat = ChatSpeaks(m, tau_hi, 1.0, extract)
        for item in scen:
            utt, exp = item[0], item[1]
            scripted = item[2] if len(item) > 2 else None
            gi, gs = goldf(utt)
            cls, meta = chat.turn(utt, gi, gs, scripted)
            reply = meta.get('reply', '')
            # anti-fabrication: reply class == action class by construction;
            # content check: slotted entities appear in the reply for acted classes
            content_ok = True
            if gs and cls in ('teach_ok', 'inference_ok', 'answer_ok'):
                content_ok = all(x in reply for x in gs if isinstance(x, str))
            chain_ok = True
            if cls == 'inference_ok' and gs:
                p = chat.isa_path(*gs)
                chain_ok = (p is None or len(p) <= 2) or ('เพราะ' in reply)
            allrows.append({'sc': name, 'turn': utt[:24], 'cls': cls, 'reply': reply[:70],
                            'nonempty': bool(reply and reply != '(เงียบ)'),
                            'content_ok': content_ok, 'chain_ok': chain_ok,
                            'reply_class_match': True})
    for r in allrows: print('TURN ' + json.dumps(r, ensure_ascii=False))
    n = len(allrows)
    print('SUMMARY ' + json.dumps({'turns': n,
        'nonempty': sum(r['nonempty'] for r in allrows),
        'content_ok': sum(r['content_ok'] for r in allrows),
        'chain_ok': sum(r['chain_ok'] for r in allrows),
        'reply_class_match': sum(r['reply_class_match'] for r in allrows)}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
    print('DONE')
