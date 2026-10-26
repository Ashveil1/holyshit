"""B-605: wrong-intent mutation guard battery - unfamiliar question/teach
compositions with per-turn mutation accounting. Pre-registered in
LEDGER.md B-605. Usage: python3 b605.py
"""
import json, time
from b570 import Watchdog, BUDGET
from hsml_chat import fresh_chat

# (user line, expect_no_mutation, note)
SCRIPT = [('ควายมีเขา', False, 'teach novel composition'),
          ('ใช่', False, 'confirm teach'),
          ('เป็ดเป็นนก', False, 'teach'), ('ใช่', False, ''),
          ('เสือมีขน', False, 'teach'), ('ใช่', False, ''),
          ('ช้างมีงา', False, 'teach'), ('ใช่', False, ''),
          ('ควายมีเขาไหม', True, 'known question - answer, no mutation'),
          ('ใช่', True, 'confirm question guess'),
          ('เป็ดเป็นหมาไหม', True, 'unknown question - honest, no mutation'),
          ('ใช่', True, ''),
          ('ช้างไม่มีงาจริงไหม', True, 'retraction-QUESTION - must not delete ช้าง/งา'),
          ('ใช่', True, ''),
          ('หมูมีเขาหรือเปล่า', True, 'unknown entity question'),
          ('ใช่', True, ''),
          ('งาของช้างคืออะไร', True, 'ask_attr known - answer, no mutation'),
          ('ใช่', True, '')]
EXPECTED_ISA = {('เป็ด', 'นก')}
EXPECTED_ATTR = {('ควาย', 'เขา'), ('เสือ', 'ขน'), ('ช้าง', 'งา')}

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    chat = fresh_chat()
    violations = []; mutations = []; replies = []
    def stores():
        return ({(k, v) for k, vs in chat.isa.items() for v in vs},
                {(k, v) for k, vs in chat.attr.items() for v in vs})
    for line, no_mut, note in SCRIPT:
        before = stores()
        reply = chat.user_turn(line)
        after = stores()
        mutated = before != after
        if mutated:
            mutations.append({'turn': line, 'added_isa': sorted(after[0]-before[0]),
                              'added_attr': sorted(after[1]-before[1]),
                              'removed_isa': sorted(before[0]-after[0]),
                              'removed_attr': sorted(before[1]-after[1])})
        if no_mut and mutated:
            violations.append({'turn': line, 'note': note})
        replies.append({'in': line, 'out': reply[:80], 'mutated': mutated, 'note': note})
    for r in replies: print('TURN ' + json.dumps(r, ensure_ascii=False))
    isa = {(k, v) for k, vs in chat.isa.items() for v in vs}
    attr = {(k, v) for k, vs in chat.attr.items() for v in vs}
    final_ok = isa == EXPECTED_ISA and attr == EXPECTED_ATTR
    print('MUTATIONS ' + json.dumps(mutations, ensure_ascii=False))
    print('SUMMARY ' + json.dumps({'question_turn_mutations': violations,
        'retraction_survived': ('ช้าง', 'งา') in attr,
        'final_store_exact': final_ok,
        'mutating_turns': len(mutations)}, ensure_ascii=False))
    ok = not violations and ('ช้าง', 'งา') in attr and final_ok
    print('CHECK ' + ('PASS' if ok else 'FAIL'))
    watchdog.stop()
    print('RES ' + json.dumps({'peak_rss_mb': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
