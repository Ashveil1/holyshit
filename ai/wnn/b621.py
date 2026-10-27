"""Entity permutation augmentation, no episodic support or model changes."""
import collections,hashlib,inspect,json,random,time
import b570 as P
import b562 as B
from b562_diag import build
from b564 import NEW_EVAL_FAM
spec=json.load(open('b621_spec.json'));start=time.monotonic()
# Exact original training implementation, change stopping protocol only.
source=inspect.getsource(P.train_one)
a=source.index('        # early stop on dev intent acc');b=source.index('    return m, time.time() - t0',a)
source=source[:a]+source[b:]
ns=dict(P.__dict__);exec(compile(source,'b621_fixed_epoch_training','exec'),ns);train=ns['train_one']

def transform(rows,mapping=None,shuffle=None):
 out=[];cursor=0
 for s,d,slots,fi in rows:
  ts=s.split();positions=P.gold_positions(s,slots);new=[]
  replacements={}
  for old,pos in zip(slots,positions):
   if pos<0:raise ValueError('gold slot missing')
   if pos not in replacements:
    val=shuffle[cursor] if shuffle is not None else mapping.get(old,old)
    cursor+=1;replacements[pos]=val;ts[pos]=val
   new.append(replacements[pos])
  out.append((' '.join(ts),d,tuple(new),fi))
 return out

def metric(model,rows):
 intent=slots=joint=0
 for s,d,g,_ in rows:
  p,sl=P.ptr_predict(model,s);i=p==d;q=tuple(sl)==tuple(g)
  intent+=i;slots+=q;joint+=i and q
 return {'n':len(rows),'intent':intent,'slots_all_items':slots,'joint':joint}

if __name__=='__main__':
 results=[];audits=[]
 for seed in spec['seeds']:
  rng,tr,dev,*_=build(seed)
  words=sorted({v for _,_,sl,_ in tr for v in sl})
  mapping={w:f'Ent{i:03d}' for i,w in enumerate(words)}
  renamed=transform(tr,mapping)
  bag=[s.split()[pos] for s,d,sl,fi in renamed for pos in dict.fromkeys(P.gold_positions(s,sl))]
  shuf=list(bag);random.Random(seed+789).shuffle(shuf)
  randomized=transform(tr,shuffle=shuf)
  def allhash(rows):return collections.Counter(fid for s,d,sl,fi in rows for ids in P.tok_feats(s) for fid in ids)
  assert allhash(renamed)==allhash(randomized)
  assert all(-1 not in P.gold_positions(s,sl) for s,d,sl,fi in randomized)
  hashes=[f for w in mapping.values() for ids in P.tok_feats(w) for f in ids]
  audits.append({'seed':seed,'slot_occurrences':len(bag),'synthetic_feature_occurrences':len(hashes),
                 'unique_hash_buckets':len(set(hashes)),'same_entity_multiset':True,'all_input_hash_multiset_equal':True,'valid_examples':len(randomized),'updates_each':len(randomized)*12})
  cells={}
  for t,newtemplate in [('seenT',False),('unseenT',True)]:
   for e,unseen in [('seenE',False),('unseenE',True)]:
    rows=[it for d in B.INTENTS for it in B.gen(rng,d,NEW_EVAL_FAM[d] if newtemplate else B.FAM[d], B.EVAL_VOCAB[d] if unseen else B.VOCAB[d],8)]
    cells[t+'_'+e]=rows
  for arm,data in [('ordinary',tr),('static_rename',renamed),('entity_shuffle',randomized)]:
   if time.monotonic()-start>90:raise TimeoutError('fixed bound')
   m,_=train(data,[],seed,epochs=12)
   for cell,rows in cells.items():
    if arm!='ordinary':
     emap={w:(f'Novel{i:03d}' if 'unseenE' in cell else mapping.get(w,f'Missing{i:03d}')) for i,w in enumerate(sorted({v for _,_,sl,_ in rows for v in sl}))}
     evaluated=transform(rows,emap)
    else:evaluated=rows
    results.append({'seed':seed,'arm':arm,'cell':cell,**metric(m,evaluated)})
 print('SPEC-SHA256 '+hashlib.sha256(open('b621_spec.json','rb').read()).hexdigest())
 print('TRAIN-SOURCE-SHA256 '+hashlib.sha256(source.encode()).hexdigest())
 print('AUDIT '+json.dumps(audits))
 print('RESULTS '+json.dumps(results))
 pool={a:{k:sum(r[k] for r in results if r['arm']==a and 'unseenE' in r['cell']) for k in ['n','intent','joint']} for a in spec['arms']}
 passed=all(pool['entity_shuffle'][k]>pool[a][k] for a in ['ordinary','static_rename'] for k in ['intent','joint'])
 print('POOLED '+json.dumps(pool));print('WALL '+str(time.monotonic()-start));print('CHECK PASS' if passed else 'CHECK NULL')
