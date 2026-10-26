"""Original ambiguous-signature local contrast, not SGOLL reproduction."""
import collections,itertools,json,math,time
from b613 import SPEC,tup,execute,size,shape
START=time.monotonic()

def subtrees(t):
    out={t}
    for c in t[1:]:out|=subtrees(c)
    return out

def phrases(s):
    w=s.split();return set(w+[' '.join(w[i:i+2]) for i in range(len(w)-1)])

def main():
    levels={1:[(a,) for a in SPEC['grammar']['atoms']]}
    for n in range(2,6):
        levels[n]=[('not',t) for t in levels[n-1]]
        for i in range(1,n-1):
            for a,b in itertools.product(levels[i],levels[n-1-i]):
                levels[n].extend([(op,a,b) for op in ['and','or']])
    trees=sum(levels.values(),[]);assert len(trees)==852
    sig={t:execute(t) for t in trees};subs={t:subtrees(t) for t in trees}
    bysig=collections.defaultdict(list)
    for t in trees:bysig[sig[t]].append(t)
    # Only signatures passed to learner.
    train=[(s,execute(tup(t))) for s,t in SPEC['training']]
    translate=lambda s:' '.join(SPEC['thai_tokens'][w] for w in s.split())
    train+= [(translate(s),v) for s,v in list(train)]
    tests=[(s,tup(t)) for s,t in SPEC['test']]
    tests += [(translate(s),t) for s,t in list(tests)]
    expected={}
    for v,ts in bysig.items():
        c=collections.Counter()
        for t in ts:
            for st in subs[t]:c[st]+=1/len(ts)
        expected[v]=c
    frozen=json.loads(next(l[8:] for l in open('logs/b613_run1.log') if l.startswith('RESULTS ')))
    baseline={k:{m:v[m] for m in ['exact','denotation']} for k,v in frozen['arms'].items()}
    out={}
    for arm in ['local','permuted','no_feedback','memorization']:
        counts=collections.Counter();joint=collections.defaultdict(collections.Counter)
        total=collections.Counter();memory={};rows=[]
        for step in range(1,97):
            if time.monotonic()-START>60:raise TimeoutError('frozen wall bound')
            i=(step-1)%24;text,v=train[i]
            if arm=='permuted':v=train[(i+1)%24][1]
            if arm!='no_feedback':
                for st,p in expected[v].items():total[st]+=p
                for w in phrases(text):
                    counts[w]+=1;joint[w].update(expected[v])
                memory[text]=v
            if step not in [1,4,12,24,48,96]:continue
            answers=[]
            for text,gold in tests:
                def score(t):
                    if arm=='memorization':return float(memory.get(text,-1)==sig[t])
                    if arm=='no_feedback':return 0.
                    s=0.
                    for w in phrases(text):
                        n=counts[w]
                        if not n:continue
                        for st in subs[t]:
                            present=joint[w][st]/n
                            absent=(total[st]-joint[w][st])/(step-n) if step>n else 0.
                            s+=present-absent
                    return s
                beam=[]
                for n,ts in levels.items():beam+=sorted(ts,key=lambda t:(-score(t),repr(t)))[:64]
                guess=min(beam,key=lambda t:(-score(t),repr(t)))
                answers.append({'text':text,'guess':guess,'exact':guess==gold,
                                'denotation':sig[guess]==execute(gold),'beam_gold':gold in beam})
            rows.append({'presentations':step,'teacher_selections':0 if arm=='no_feedback' else step,
                         'state_observations':0 if arm=='no_feedback' else step*16,
                         'unique_contexts':min(step,24),
                         'exact':sum(a['exact'] for a in answers),
                         'denotation':sum(a['denotation'] for a in answers),
                         'beam_gold':sum(a['beam_gold'] for a in answers),'answers':answers})
        out[arm]=rows
    final=out['local'][-1]['denotation']
    passed=final>baseline['fragment']['denotation'] and all(final>out[k][-1]['denotation'] for k in ['permuted','no_feedback'])
    print('RESULTS '+json.dumps({'arms':out,'frozen_baseline':baseline},ensure_ascii=False))
    print('WALL '+str(time.monotonic()-START))
    print('CHECK PASS' if passed else 'CHECK NULL')
if __name__=='__main__':main()
