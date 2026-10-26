"""Frozen-protocol consolidation of the learned-language line (B-562..B-565).

Parses the committed run logs and emits ONE consolidated table. No training,
no eval re-scoring, no new data: this is a reproducible view over recorded
runs. Protocols are kept separate: B-562 = gated (abstention) numbers;
B-564/565 = raw argmax (labeled), abstention reported separately.

Frozen protocol facts:
  intents: 8 (teach_attr, ask_attr, retract_attr, teach_isa, is_a_q,
              name_skill, give_example, confirm_answer)
  train:   64 examples/seed (8 per intent)
  eval:    64 examples per set (8 per intent)
    frozen  - INSPECTED many rounds (B-562 era), reference only
    newtmpl - INSPECTED once (B-564/565)
    fresh3  - authored at B-565, unfamiliar entity set #2
  mapper:  S1 uniform-prior NB (frozen since B-564)
Usage: python3 b_consol.py  (reads logs/b562_run4.log, logs/b565_run1.log)
"""
import json, io

def rows(path, prefix):
    out = []
    for line in io.open(path, encoding='utf-8'):
        line = line.strip()
        if line.startswith(prefix):
            out.append(json.loads(line[len(prefix):]))
    return out

# --- B-562 gated aggregate (frozen eval, 5 seeds) ---
agg = rows('logs/b562_run4.log', 'AGG ')[0]
print('== B-562 GATED (frozen eval, means over 5 seeds) ==')
print('arm        k  intent  slotf1  joint  wrong_forced')
for arm in ['wnn', 'nb', 't2p', 'nn1']:
    for k in ['1', '2', '4', '8']:
        m = agg[arm][k]
        print('%-9s %2s  %.3f   %.3f   %.4f  %s' % (arm, k, m['intent'], m['slotf1'], m['joint'], m['wrong_forced']))
print('frames intent %.3f | majority intent %.3f (all k)' % (agg['frames']['1']['intent'], agg['majority']['1']['intent']))

# --- B-565 raw-argmax per-seed paired table ---
r = [x for x in rows('logs/b565_run1.log', 'ROW ') if 'extractor' in x]
print()
print('== B-565 RAW-ARGMAX (per seed, S3 vs S4; abstention separate) ==')
for ev in ['frozen_INSPECTED', 'newtmpl_INSPECTED1', 'fresh3']:
    print('-- %s (n=64 per seed) --' % ev)
    print('seed  S3.joint  S4.joint  d.joint  S3.slotx  S4.slotx  d.slotx  intent  wrong_act(S3/S4)  abstain_SEP(S3/S4)')
    dj, ds = [], []
    for seed in range(5):
        s3 = next(x for x in r if x['seed'] == seed and x['extractor'] == 'S3' and x['eval'] == ev)
        s4 = next(x for x in r if x['seed'] == seed and x['extractor'] == 'S4' and x['eval'] == ev)
        d1 = s4['joint'] - s3['joint']; d2 = s4['slot_exact_on_correct'] - s3['slot_exact_on_correct']
        dj.append(d1); ds.append(d2)
        print('%4d  %8.3f  %8.3f  %+7.3f  %9.3f  %9.3f  %+7.3f  %.3f  %d/%d  %d/%d' % (
            seed, s3['joint'], s4['joint'], d1, s3['slot_exact_on_correct'], s4['slot_exact_on_correct'], d2,
            s4['intent'], s3['wrong_action'], s4['wrong_action'], s3['abstain_gated_SEPARATE'], s4['abstain_gated_SEPARATE']))
    m3 = sum(x['joint'] for x in r if x['extractor'] == 'S3' and x['eval'] == ev) / 5
    m4 = sum(x['joint'] for x in r if x['extractor'] == 'S4' and x['eval'] == ev) / 5
    print('mean S3 %.3f  S4 %.3f  | paired d.joint seeds %s | d.slotx seeds %s' % (
        m3, m4, ['%+.3f' % d for d in dj], ['%+.3f' % d for d in ds]))
print()
print('DONE')
