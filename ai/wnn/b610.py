"""B610 v2: proposal-only context/intent association. See LEDGER gates.
No Chat instance, action executor, or entry behavior modifications."""
import json
from collections import Counter
import b562 as B
from b562_diag import build
from b564 import NBu
from b570 import Watchdog, BUDGET

CONTEXT = {'teach_isa': 'ประโยคถัดไปฉันจะสอนข้อเท็จจริง',
           'is_a_q': 'ประโยคถัดไปฉันจะถามคำถาม'}
TRAIN = [('ม้า','สัตว์เลี้ยง'), ('แพะ','สัตว์เลี้ยง'),
         ('ควาย','สัตว์ป่า'), ('เป็ด','นก')]
TEST_ISA = [('ลิง','สัตว์ป่า'), ('กบ','สัตว์'),
            ('หมี','สัตว์ป่า'), ('แพนด้า','สัตว์เลี้ยง')]
TEST_HAS = [('มิโล','หาง'), ('บัว','กลีบ')]
assert not ({x for x,y in TRAIN} & {x for x,y in TEST_ISA+TEST_HAS})


def encode(surface, context, use_context):
    f = B.encode(surface)
    if use_context:
        # Fixed encoder namespaces, not intent-specific routing.
        f.update({'ctx:'+k:v for k,v in B.encode(context).items()})
    return f


def make():
    _, train, *_ = build(0)
    m = NBu(B.INTENTS)
    for s,d,_,_ in train: m.add(B.encode(s), d)
    return m


def metrics(rows):
    cm = Counter((r['gold'],r['guess']) for r in rows)
    per = {}
    for d in CONTEXT:
        tp = cm[d,d]
        predicted = sum(v for (g,p),v in cm.items() if p==d)
        actual = sum(v for (g,p),v in cm.items() if g==d)
        per[d] = {'precision':tp/predicted if predicted else None,
                  'recall':tp/actual if actual else None}
    correct = sum(r['gold']==r['guess'] for r in rows)
    return {'n':len(rows),'correct':correct,'accuracy':correct/len(rows),
            'confusion':{g+' -> '+p:v for (g,p),v in sorted(cm.items())},
            'per_class':per,
            'binary_reviewer_feedback_turns':len(rows)+(len(rows)-correct),
            'reviewer_model':'one yes for a correct proposal; no then yes for wrong proposal',
            'real_repl_assisted_success':'not measured'}


def run():
    watchdog = Watchdog(BUDGET); watchdog.start()
    arms = {'surface_only':(False,True,False),
            'context_feedback':(True,True,False),
            'context_no_feedback':(True,False,False),
            'context_swapped_labels':(True,True,True)}
    results = {}
    for arm,(ctx,learn,swap) in arms.items():
        m = make()
        if learn:
            for x,y in TRAIN:
                s = x+' เป็น '+y
                for gold,context in CONTEXT.items():
                    label = ('is_a_q' if gold=='teach_isa' else 'teach_isa') if swap else gold
                    m.add(encode(s,context,ctx),label)
        rows = []
        for shape,pairs,verb in [('known_shape_new_entity',TEST_ISA,'เป็น'),
                                 ('session_heldout_structure',TEST_HAS,'มี')]:
            for x,y in pairs:
                s = x+' '+verb+' '+y
                for gold,context in CONTEXT.items():
                    guess,margin = B.predict(m,encode(s,context,ctx),-1e18)
                    rows.append({'shape':shape,'surface':s,'context':context,
                                 'gold':gold,'guess':guess,'margin':margin})
        results[arm] = {'rows':rows, 'all':metrics(rows),
                        'by_shape':{sh:metrics([r for r in rows if r['shape']==sh])
                                    for sh in {r['shape'] for r in rows}}}
    a = {k:v['all']['accuracy'] for k,v in results.items()}
    gate = (a['context_feedback']>a['surface_only'] and
            a['context_feedback']>a['context_no_feedback'] and
            a['context_feedback']>a['context_swapped_labels'])
    watchdog.stop()
    print('RESULTS '+json.dumps(results,ensure_ascii=False))
    print('AMBIGUITY '+json.dumps({'uncued_surface':'ลิง เป็น สัตว์ป่า',
          'compatible_intents':['teach_isa','is_a_q'],
          'hidden_gold_accuracy':'not defined','required_response':'clarification'},ensure_ascii=False))
    print('RES '+json.dumps({'peak_rss_bytes':watchdog.peak}))
    print('GATE '+json.dumps({'accuracies':a,'hypothesis_supported':gate}))
    print('CHECK PASS' if gate else 'CHECK NULL')
if __name__=='__main__': run()
