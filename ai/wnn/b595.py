"""B-595: segmentation -> unified pipeline reachability. Usage: python3 b595.py"""
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
from b592 import HSMLChat
from b589 import LEX, segment

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t0 = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    chat_spaced = HSMLChat(m, tau_hi, 1.0, extract)
    chat_despace = HSMLChat(m, tau_hi, 1.0, extract)
    parity = 0; rows = []
    for utt, exp, scripted, note in V1:
        gi, gs = GOLD[utt]
        cls_sp, _ = chat_spaced.turn(utt, gi, gs, scripted)
        despaced = utt.replace(' ', '')
        seg = ' '.join(segment(despaced, LEX))
        cls_de, _ = chat_despace.turn(seg, gi, gs, scripted)
        ok = cls_sp == cls_de
        parity += ok
        rows.append({'turn': utt[:26], 'segmented': seg[:40], 'spaced_cls': cls_sp,
                     'despaced_cls': cls_de, 'parity': ok,
                     'seg_matches_ref': seg == utt})
    for r in rows: print('TURN ' + json.dumps(r, ensure_ascii=False))
    print('SUMMARY ' + json.dumps({'parity': parity, 'turns': len(V1),
        'seg_exact': sum(r['seg_matches_ref'] for r in rows)}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak/1e6,1), 'wall_seconds': round(time.time()-t0,1)}))
    print('DONE')
