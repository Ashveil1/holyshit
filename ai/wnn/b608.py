"""B-608: induced patterns proposal-only + adversarial battery + real-REPL
check. Pre-registered in LEDGER.md B-608. Usage: python3 b608.py
"""
import json, subprocess, sys, time
from b570 import Watchdog, BUDGET
from hsml_chat import fresh_chat

def stores(c):
    return ({(k, v) for k, vs in c.isa.items() for v in vs},
            {(k, v) for k, vs in c.attr.items() for v in vs})

def teach_isa3(c):
    for line in ['มิโลเป็นแมว', 'บัวเป็นดอกไม้', 'ช้างเป็นสัตว์ป่า']:
        c.user_turn(line); c.user_turn('ใช่')

def battery():
    res = {}
    c = fresh_chat()
    teach_isa3(c)
    res['proposal_text'] = '...'
    # approve pattern via pattern_awaiting
    res['pattern_awaiting'] = c.pattern_awaiting is not None
    res['proposal'] = c.user_turn('ใช่')
    # G1: new instances -> pattern-INFORMED proposals, correct parse, no write before yes
    prop_ok = 0; wrong_prop = 0
    for line, want in [('วัวเป็นสัตว์เลี้ยง', ('วัว', 'สัตว์เลี้ยง')),
                       ('แพะเป็นสัตว์เลี้ยง', ('แพะ', 'สัตว์เลี้ยง')),
                       ('ควายเป็นสัตว์ป่า', ('ควาย', 'สัตว์ป่า'))]:
        b = stores(c)
        r = c.user_turn(line)
        a = stores(c)
        if b != a: wrong_prop += 1; continue   # wrote without yes: error
        good = 'ตามรูปแบบ' in r and all(w in r for w in want)
        prop_ok += good
        if not good: wrong_prop += 1
        res.setdefault('new_proposals', []).append(r)
        c.user_turn('ใช่')   # accept -> then it writes
    res['new_proposals_correct'] = prop_ok; res['wrong_proposals'] = wrong_prop
    # G2: near-misses must produce NO wrong-write proposal
    nm_bad = []
    EXPECT = {'ม้าไม่มีเขา': 'retract_ok',          # correct: proposes ไม่มี write
              'ม้าเป็นสัตว์ไหม': 'question_ok',      # question proposal, no write
              'เป็ดเป็นนกมาก': 'no_write_proposal',  # completeness: มาก unparsed
              'เขาบอกว่าวัวเป็นสัตว์เลี้ยง': 'no_write_proposal'}
    for line, exp in EXPECT.items():
        b = stores(c); w0 = c.writes
        r = c.user_turn(line)
        a = stores(c)
        if b != a or c.writes != w0:
            nm_bad.append(('wrote', line, r))
        elif exp == 'retract_ok' and 'ไม่มี' not in r:
            nm_bad.append(('bad_retract_proposal', line, r))
        elif exp == 'question_ok' and 'สอนว่า' in r:
            nm_bad.append(('proposed_write', line, r))
        elif exp == 'no_write_proposal' and 'สอนว่า' in r:
            nm_bad.append(('proposed_write', line, r))
        res.setdefault('nm_replies', []).append({'in': line, 'out': r[:90]})
        if c.pending is not None: c.user_turn('ไม่ใช่')
    res['near_miss_bad'] = nm_bad
    # G2b: quoted NEW fact (not yet in store) - masked-write probe
    b = stores(c); w0 = c.writes
    rq = c.user_turn('เขาบอกว่าลิงเป็นสัตว์เลี้ยง')
    res['quoted_new_fact'] = {'reply': rq[:90], 'wrote': c.writes != w0 or stores(c) != b}
    if c.pending is not None: c.user_turn('ไม่ใช่')
    # G3: conflict - induce a colliding pattern with different intent
    for line in ['แมวมีหาง', 'หมามีหาง', 'นกมีปีก']:
        c.user_turn(line); c.user_turn('ใช่')
    if c.pattern_awaiting: c.user_turn('ใช่')   # activate '<X> มี <Y>'
    b = stores(c)
    r = c.user_turn('สัตว์ป่าเป็นสัตว์')   # matches isa pattern only (shape differs) - sanity
    res['no_collision_on_normal'] = 'ตามรูปแบบ' in r
    if c.pending is not None: c.user_turn('ใช่')
    res['after'] = sorted(map(list, stores(c)[0]))
    res['total_writes'] = c.writes
    print('RESULTS ' + json.dumps(res, ensure_ascii=False))
    return res

def real_repl():
    """Drive the ACTUAL entry via stdin/stdout, two real processes."""
    lines1 = ['มิโลเป็นแมว', 'ใช่', 'บัวเป็นดอกไม้', 'ใช่', 'ช้างเป็นสัตว์ป่า', 'ใช่',
              'ใช่', 'วัวเป็นสัตว์เลี้ยง', 'ใช่', 'save']
    p1 = subprocess.run([sys.executable, 'hsml_chat.py'], input='\n'.join(lines1) + '\n',
                        capture_output=True, text=True, timeout=60)
    out1 = p1.stdout
    saw_proposal = 'สังเกตว่าประโยคแบบ' in out1
    saw_pattern_proposal = 'ตามรูปแบบที่จำไว้' in out1
    saw_saved = 'บันทึกแล้ว' in out1
    p2 = subprocess.run([sys.executable, 'hsml_chat.py', '--load', 'logs/hsml_snapshot.json'],
                        input='แพะเป็นสัตว์เลี้ยง\nใช่\n', capture_output=True, text=True, timeout=60)
    out2 = p2.stdout
    restart_ok = 'ตามรูปแบบที่จำไว้' in out2 and 'แพะ' in out2
    res = {'saw_induction_proposal': saw_proposal, 'saw_pattern_informed': saw_pattern_proposal,
           'saved': saw_saved, 'restart_pattern_active': restart_ok}
    print('REAL-REPL ' + json.dumps(res, ensure_ascii=False))
    return res

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    res = battery()
    repl = real_repl()
    ok = (res['pattern_awaiting'] and res['new_proposals_correct'] == 3
          and res['wrong_proposals'] == 0 and not res['near_miss_bad']
          and not res['quoted_new_fact']['wrote'] and res['no_collision_on_normal']
          and all(repl.values()))
    print('CHECK ' + ('PASS' if ok else 'FAIL'))
    watchdog.stop()
    print('RES ' + json.dumps({'peak_rss_mb': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
