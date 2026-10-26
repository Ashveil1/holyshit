"""B-607: LEARNED teacher-dependence reduction - pattern induction from
confirm-yes instances. Pre-registered in LEDGER.md B-607.
Usage: python3 b607.py
"""
import json, time
from b570 import Watchdog, BUDGET
from hsml_chat import fresh_chat

def stores(c):
    return ({(k, v) for k, vs in c.isa.items() for v in vs},
            {(k, v) for k, vs in c.attr.items() for v in vs})

def teach3(c):
    """Three novel-entity instances of '<E1> เป็น <E2>' via confirms."""
    qs = 0
    for line in ['มิโลเป็นแมว', 'บัวเป็นดอกไม้', 'ช้างเป็นสัตว์ป่า']:
        q0 = c.q
        c.user_turn(line)
        r = c.user_turn('ใช่')
        qs += c.q - q0
    return qs

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    results = {}
    # --- induced chat ---
    c = fresh_chat()
    q_teach = teach3(c)
    results['questions_during_3_teaches'] = q_teach
    results['pattern_pending'] = c.pattern_awaiting is not None
    r_prop = c.user_turn('ใช่')          # approve induced pattern
    results['proposal_reply'] = r_prop
    # G1: NEW novel-entity instances unassisted, 0 questions, correct slots
    un = 0; wrong = 0; q_new = 0
    for line, want in [('วัวเป็นสัตว์เลี้ยง', ('วัว', 'สัตว์เลี้ยง')),
                       ('แพะเป็นสัตว์เลี้ยง', ('แพะ', 'สัตว์เลี้ยง')),
                       ('ควายเป็นสัตว์ป่า', ('ควาย', 'สัตว์ป่า'))]:
        q0 = c.q; b = stores(c)
        r = c.user_turn(line)
        a = stores(c)
        q_new += c.q - q0
        wrote = b != a
        if wrote and (want[0], want[1]) in a[0]: un += 1
        elif wrote: wrong += 1
        results.setdefault('new_replies', []).append({'in': line, 'out': r, 'q': c.q - q0})
    results['new_unassisted_correct'] = un; results['new_wrong'] = wrong
    results['new_questions'] = q_new
    # G2: near-misses - no writes
    nm_writes = []
    for line in ['ม้าเป็นสัตว์ไหม', 'ม้าเป็น', 'เป็ดเป็นนกมาก']:
        b = stores(c); c.user_turn(line); a = stores(c)
        if b != a: nm_writes.append(line)
        if c.pending is not None: c.user_turn('ไม่ใช่')  # decline any guess
    results['near_miss_writes'] = nm_writes
    # G3: control chat WITHOUT induction - same new instances each need >=1 question
    ctrl = fresh_chat()
    teach3(ctrl)
    ctrl.user_turn('ไม่ใช่')   # reject the proposal -> per-instance questions stay
    ctrl_q = 0
    for line in ['วัวเป็นสัตว์เลี้ยง', 'แพะเป็นสัตว์เลี้ยง', 'ควายเป็นสัตว์ป่า']:
        q0 = ctrl.q; ctrl.user_turn(line); ctrl_q += ctrl.q - q0
        if ctrl.pending is not None: ctrl.user_turn('ใช่')
    results['control_questions_on_new'] = ctrl_q
    # G5: induced pattern survives a snapshot/restore
    snap = c.snapshot()
    c2 = fresh_chat(); c2.restore(snap)
    q0 = c2.q
    r2 = c2.user_turn('ลิงเป็นสัตว์ป่า')
    results['post_restore_unassisted'] = ('ลิง', 'สัตว์ป่า') in stores(c2)[0] and c2.q == q0
    results['post_restore_reply'] = r2
    results['final_isa'] = sorted(map(list, stores(c)[0]))
    print('RESULTS ' + json.dumps(results, ensure_ascii=False))
    ok = (results['pattern_pending'] and un == 3 and wrong == 0 and q_new == 0
          and not nm_writes and ctrl_q >= 3 and results['post_restore_unassisted'])
    print('CHECK ' + ('PASS' if ok else 'FAIL'))
    watchdog.stop()
    print('RES ' + json.dumps({'peak_rss_mb': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
