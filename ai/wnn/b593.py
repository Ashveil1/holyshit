"""B-593: persistence probe - actual JSON snapshot across a real process
boundary. Usage: python3 b593.py save | python3 b593.py load
"""
import json, sys, time
from collections import defaultdict, Counter
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET
from b574 import pick_tau_precision
from b592 import HSMLChat
from b591b import compile_def

SNAP = 'logs/b593_snapshot.json'

def fresh():
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    return HSMLChat(m, tau_hi, 1.0, extract), train

def snapshot(chat):
    return {
        'isa': {k: sorted(v) for k, v in chat.isa.items()},
        'attr': {k: sorted(v) for k, v in chat.attr.items()},
        'mapper_fc': {d: dict(c) for d, c in chat.m.fc.items()},
        'mapper_tot': dict(chat.m.tot),
        'defs': [[d[1]] for d in chat.defs],  # source strings; rules rebuilt via supplied compiler on load
        'seen': sorted(chat.seen),
    }

if __name__ == '__main__':
    mode = sys.argv[1]
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    chat, train = fresh()
    if mode == 'save':
        chat.turn('มิโล เป็น แมว', 'teach_isa', ('มิโล', 'แมว'))
        chat.turn('แมว เป็น สัตว์', 'teach_isa', ('แมว', 'สัตว์'))
        chat.turn('นิยาม เหยี่ยว น่ะ เป็น นก เหมือน เหยี่ยว เป็น นก ตัวแปร 1,4', None, None)
        chat.turn('แมวตัวนี้ชื่อมิโลนะ', 'teach_isa', ('มิโล', 'แมว'), ('teach_isa', ('มิโล', 'แมว')))  # in-band correction
        snap = snapshot(chat)
        with open(SNAP, 'w') as f: json.dump(snap, f, ensure_ascii=False)
        print('SAVED ' + json.dumps({'isa_size': len(snap['isa']), 'defs': len(snap['defs']),
            'fc_intents': len(snap['mapper_fc'])}, ensure_ascii=False))
    else:
        with open(SNAP) as f: snap = json.load(f)
        chat.isa = defaultdict(set, {k: set(v) for k, v in snap['isa'].items()})
        chat.attr = defaultdict(set, {k: set(v) for k, v in snap['attr'].items()})
        chat.m.fc = {d: Counter(c) for d, c in snap['mapper_fc'].items()}
        chat.m.tot = Counter(snap['mapper_tot'])
        for (src,) in snap['defs']:
            body = src[6:]
            lhs, rest = body.split(' เหมือน ', 1)
            canon, varstr = rest.split(' ตัวแปร ', 1)
            chat.defs.append((compile_def(lhs.split(), canon.split(), [int(x)-1 for x in varstr.split(',')]), src))
        chat.seen = set(snap['seen'])
        # exact-equality check: re-snapshot and compare
        snap2 = snapshot(chat)
        equal = json.dumps(snap, sort_keys=True, ensure_ascii=False) == json.dumps(snap2, sort_keys=True, ensure_ascii=False)
        # taught item must answer WITHOUT a question; untaught unfamiliar must still ask
        q0 = chat.q
        cls1, _ = chat.turn('มิโล เป็น สัตว์ ไหม', 'is_a_q', ('มิโล', 'สัตว์'))
        q_after_taught = chat.q - q0
        cls2, _ = chat.turn('แมวตัวนี้ชื่อมิโลนะ', 'teach_isa', ('มิโล', 'แมว'))  # seen surface -> literal_repeat, no re-ask
        q0 = chat.q
        cls3, _ = chat.turn('ตัวอะไร บิน ได้บ้าง', None, None)  # untaught unfamiliar
        q_after_unfamiliar = chat.q - q0
        cls4, meta4 = chat.turn('กวาง น่ะ เป็น สัตว์', 'teach_isa', ('กวาง', 'สัตว์'))  # persisted definition fires
        print('LOAD ' + json.dumps({'snapshot_roundtrip_equal': equal,
            'taught_infer': cls1, 'questions_for_taught': q_after_taught,
            'seen_surface': cls2,
            'unfamiliar': cls3, 'questions_for_unfamiliar': q_after_unfamiliar,
            'persisted_definition_fires': meta4.get('definition_fired', False), 'def_turn': cls4}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
    print('DONE')
