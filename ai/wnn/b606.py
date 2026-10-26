"""B-606: question/statement ambiguity independent of markers,
confirm-before-write, quoted-content no-write, answer relevance.
Pre-registered in LEDGER.md B-606. Usage: python3 b606.py
"""
import json, time
from b570 import Watchdog, BUDGET
from hsml_chat import fresh_chat

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    chat = fresh_chat()
    def stores():
        return ({(k, v) for k, vs in chat.isa.items() for v in vs},
                {(k, v) for k, vs in chat.attr.items() for v in vs})
    results = {}
    replies = []
    def go(line, expect_write=None):
        before = stores()
        r = chat.user_turn(line)
        after = stores()
        wrote = before != after
        replies.append({'in': line, 'out': r[:90], 'wrote': wrote})
        if expect_write is not None and wrote != expect_write:
            results.setdefault('write_violations', []).append({'turn': line, 'wrote': wrote})
        return r

    # setup: teach มิโล เป็น แมว + ช้าง มี งา (confirmed writes)
    go('มิโลเป็นแมว'); go('ใช่', expect_write=True)
    go('ช้างมีงา'); go('ใช่', expect_write=True)

    # T1: UNMARKED QUESTION - user means "is Milo a cat?" - escape hatch
    r1 = go('มิโลเป็นแมว', expect_write=False)  # literal repeat -> no question; use fresh surface
    chat2 = fresh_chat()
    chat2.user_turn('มิโลเป็นแมว'); chat2.user_turn('ใช่')
    rb = chat2.user_turn('มิโลเป็นแมวจริงไหม')  # marked question, sanity
    results['marked_known_q'] = rb
    # unmarked ambiguous surface on a fresh chat, user rejects teach guess
    chat3 = fresh_chat()
    g1 = chat3.user_turn('หมาเป็นสัตว์')          # unmarked: could be statement OR question
    esc = chat3.user_turn('ไม่ใช่')              # reject -> escape hatch opens all intents
    results['escape_first_guess'] = g1
    results['escape_second_guess'] = esc
    results['escape_reached_question'] = ('ถาม' in esc)
    if 'ถาม' in esc:
        ans = chat3.user_turn('ใช่')
        results['escape_answer'] = ans
        results['escape_answered'] = ('ไม่รู้' in ans or 'ใช่' in ans) and 'จำแล้ว' not in ans
    # T2: QUOTED CONTENT with question word inside - must not write
    rq = go('ตัวอย่างคำถามคือแมวมีหางไหม', expect_write=False)
    rq2 = go('ไม่ใช่', expect_write=False)   # reject -> escape opens teach intents
    rq3 = go('ไม่ใช่', expect_write=False)   # reject again -> honest limit, loop-break
    results['quoted_replies'] = [rq, rq2, rq3]
    results['quoted_no_write'] = stores() == ({('มิโล', 'แมว')}, {('ช้าง', 'งา')})
    results['quoted_ends_honest'] = 'นิยาม' in rq3 or 'นอกสิ่ง' in rq3
    # T3: retraction statement on confirm
    go('ช้างไม่มีงา')          # unmarked retraction statement
    go('ใช่', expect_write=True)
    results['retraction_removed'] = ('ช้าง', 'งา') not in stores()[1]
    # T4: answer relevance - คืออะไร value question, known + unknown
    go('เสือมีขน'); go('ใช่', expect_write=True)
    ck = go('ขนของเสือคืออะไร', expect_write=False)
    results['value_known_confirm'] = ck
    results['value_known_confirm_semantic'] = 'ขน ของ เสือ' in ck
    rk = go('ใช่', expect_write=False)
    cu = go('เขาของมิโลคืออะไร', expect_write=False)
    ru = go('ใช่', expect_write=False) if 'เดาว่า' in cu else cu
    results['value_known_reply'] = rk
    results['value_known_relevant'] = 'ไม่รู้รายละเอียด' in rk and 'เสือ' in rk and 'ขน' in rk
    results['value_unknown_reply'] = ru
    results['value_unknown_honest'] = 'ยังไม่เคยถูกสอน' in ru or 'ไม่รู้' in ru
    for r in replies: print('TURN ' + json.dumps(r, ensure_ascii=False))
    print('RESULTS ' + json.dumps(results, ensure_ascii=False))
    ok = (not results.get('write_violations') and results.get('escape_reached_question')
          and results.get('quoted_no_write') and results.get('quoted_ends_honest')
          and results.get('retraction_removed') and results.get('value_known_confirm_semantic')
          and results.get('value_known_relevant') and results.get('value_unknown_honest'))
    print('CHECK ' + ('PASS' if ok else 'FAIL'))
    watchdog.stop()
    print('RES ' + json.dumps({'peak_rss_mb': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
