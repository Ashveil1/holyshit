"""Fresh bounded typed-AST proposal experiment; no Chat or mutations."""
import collections,hashlib,itertools,json,math,os,time
START=time.monotonic()
SPEC=json.load(open('b613_spec.json'))
MAXTIME=SPEC['limits']['wall_seconds']
ATOMS=SPEC['grammar']['atoms'];OPS=ATOMS+['not','and','or']
CAP=SPEC['grammar']['candidate_limit'];BEAM=SPEC['grammar']['beam']

def checktime():
    if time.monotonic()-START>MAXTIME:raise TimeoutError('frozen wall bound')

def tup(x):return tuple(tup(y) if isinstance(y,list) else y for y in x)
def size(t):return 1+sum(size(c) for c in t[1:])
def shape(t):return ('leaf',) if len(t)==1 else (t[0],)+tuple(shape(c) for c in t[1:])
def execute(t):
    if len(t)==1:
        idx=ATOMS.index(t[0]);return sum(1<<s for s in range(16) if s&(1<<idx))
    a=execute(t[1])
    if t[0]=='not':return a^65535
    b=execute(t[2]);return a&b if t[0]=='and' else a|b

def features(text,t):
    words=text.split();lf=collections.Counter()
    def walk(n):
        lf['node:'+n[0]]+=1
        for i,c in enumerate(n[1:]):
            lf['edge:'+n[0]+':'+str(i)+':'+c[0]]+=1;walk(c)
    walk(t)
    wf=collections.Counter(words+[' '.join(words[i:i+2]) for i in range(len(words)-1)])
    return {(w,s):a*b for w,a in wf.items() for s,b in lf.items()}

def main():
    levels={1:[(a,) for a in ATOMS]};alltrees=list(levels[1])
    for n in range(2,SPEC['grammar']['max_nodes']+1):
        new=[('not',a) for a in levels.get(n-1,[])]
        for i in range(1,n-1):
            j=n-1-i
            for a,b in itertools.product(levels.get(i,[]),levels.get(j,[])):
                for op in ['and','or']:new.append((op,a,b))
        levels[n]=new;alltrees+=new
        if len(alltrees)>CAP:raise RuntimeError('frozen enumeration cap')
    train=[(s,tup(t)) for s,t in SPEC['training']]
    test=[(s,tup(t)) for s,t in SPEC['test']]
    assert not ({shape(t) for _,t in train}&{shape(t) for _,t in test})
    def translate(s):return ' '.join(SPEC['thai_tokens'][w] for w in s.split())
    training=train+[(translate(s),t) for s,t in train]
    testing=[('en',s,t) for s,t in test]+[('th',translate(s),t) for s,t in test]
    signatures={t:execute(t) for t in alltrees}
    outcomes=[execute(t) for _,t in training]
    report={}
    for arm in SPEC['arms']:
        weights=collections.defaultdict(float);memory={};ambiguities=[]
        for i,(text,gold) in enumerate(training):
            checktime();sig=outcomes[(i+1)%len(outcomes)] if arm=='permuted_feedback' else outcomes[i]
            compatible=[t for t in alltrees if signatures[t]==sig];ambiguities.append(len(compatible))
            if arm=='no_feedback':continue
            if arm=='memorization':memory[text]=sig;continue
            fs=[features(text,t) for t in alltrees]
            scores=[sum(weights[k]*v for k,v in f.items()) for f in fs]
            high=max(scores);ex=[math.exp(s-high) for s in scores];den=sum(ex)
            positive=sum(e for e,t in zip(ex,alltrees) if signatures[t]==sig)
            delta=collections.defaultdict(float)
            for f,e,t in zip(fs,ex,alltrees):
                coeff=(e/positive if signatures[t]==sig else 0)-e/den
                for k,v in f.items():delta[k]+=coeff*v
            for k,v in delta.items():weights[k]+=.5*v
        rows=[]
        for lang,text,gold in testing:
            checktime()
            def score(t):
                if arm=='memorization':return float(memory.get(text,-1)==signatures[t])
                if arm=='no_feedback':return 0.
                return sum(weights[k]*v for k,v in features(text,t).items())
            # Bounded per-size rank beam on frozen enumeration, no adaptive expansion.
            beam=[]
            for n,trees in levels.items():beam+=sorted(trees,key=lambda t:(-score(t),repr(t)))[:BEAM]
            guess=min(beam,key=lambda t:(-score(t),repr(t)))
            rows.append({'lang':lang,'text':text,'gold':gold,'guess':guess,
                         'oracle':gold in alltrees,'beam_gold':gold in beam,
                         'exact':guess==gold,'denotation':signatures[guess]==execute(gold)})
        report[arm]={'rows':rows,'exact':sum(r['exact'] for r in rows),
                     'denotation':sum(r['denotation'] for r in rows),
                     'beam_gold':sum(r['beam_gold'] for r in rows),
                     'teacher_selections':0 if arm=='no_feedback' else len(training),
                     'compatible_ast_counts':ambiguities}
    learned=report['fragment']['exact']
    gate=all(r['oracle'] for v in report.values() for r in v['rows']) and all(learned>v['exact'] for k,v in report.items() if k!='fragment')
    print('SPEC-SHA256 '+hashlib.sha256(open('b613_spec.json','rb').read()).hexdigest())
    print('RESULTS '+json.dumps({'candidates':len(alltrees),'arms':report},ensure_ascii=False))
    print('WALL '+str(time.monotonic()-START))
    print('CHECK PASS' if gate else 'CHECK NULL')
if __name__=='__main__':main()
