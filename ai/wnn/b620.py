"""Bounded cache, validated snapshot and restart verification."""
import copy,json,os,subprocess,sys,tempfile
from hsml_chat import fresh_chat

def ask(c,s):
 r=c.user_turn(s)
 if c.pending and c.pending.get('kind')=='confirm':r=c.user_turn('ใช่')
 return r

if __name__=='__main__':
 os.environ['HSML_QUERY_CACHE_CAP']='2';c=fresh_chat()
 for i in range(2000):c._commit(f'E{i} มี หาง ไหม','ask_attr',(f'E{i}','หาง'),'synthetic')
 checks={'cache_capped':len(c.query_interpretations)==2,
         'no_query_seen_growth':len(c.seen)==0,'no_fact_writes':c.writes==c.write_attempts==0}
 evicted=ask(c,'E0 มี หาง ไหม')
 checks['evicted_not_false_known']='รู้อยู่แล้ว' not in evicted
 c=fresh_chat();c.attr['บัว'].add('กลีบ')
 c._commit('บัว มี กลีบ ไหม','ask_attr',('บัว','กลีบ'),'diagnostic')
 checks['known']=ask(c,'บัว มี กลีบ ไหม')=='ใช่ บัว มี กลีบ'
 c.attr['บัว'].discard('กลีบ')
 checks['retracted']=ask(c,'บัว มี กลีบ ไหม').startswith('ไม่รู้ว่า บัว มี กลีบ')
 c.attr['บัว'].add('กลีบ')
 snap=c.snapshot();before=c.snapshot()
 invalid=[]
 for name in ['legacy','version','abi','query_write','bad_counts','bad_definition','bad_pattern']:
  bad=copy.deepcopy(snap)
  if name=='legacy':bad.pop('schema_version')
  elif name=='version':bad['schema_version']=99
  elif name=='abi':bad['parse_cache_abi']='unknown'
  elif name=='query_write':bad['query_interpretations']['X']=('teach_attr',('X','Y'))
  elif name=='bad_counts':bad['mapper_tot']['ask_attr']=-1
  elif name=='bad_definition':bad['defs']=['garbage']
  elif name=='bad_pattern':bad['patterns']=[['ask_attr|VAR:999','active']]
  try:c.restore(bad);invalid.append((name,False))
  except ValueError:invalid.append((name,c.snapshot()==before))
 checks['invalid_atomic_rejection']=all(v for _,v in invalid)
 # cap remains current runtime configuration, not trusted snapshot setting
 d=fresh_chat();d.restore(snap)
 checks['restored_answer']=ask(d,'บัว มี กลีบ ไหม')=='ใช่ บัว มี กลีบ'
 d.user_turn('นิยาม บัว มี กลีบ ไหม เหมือน บัว มี กลีบ ตัวแปร 1,3')
 checks['definition_invalidates']='ตัดข้อความ' in d.user_turn('บัว มี กลีบ ไหม')
 os.environ['HSML_QUERY_CACHE_CAP']='0';z=fresh_chat()
 z._commit('บัว มี กลีบ ไหม','ask_attr',('บัว','กลีบ'),'diagnostic')
 checks['zero_disabled']=not z.query_interpretations and not z.seen
 os.environ['HSML_QUERY_CACHE_CAP']='2'
 fd,path=tempfile.mkstemp(suffix='.json',dir='logs');os.close(fd)
 try:
  with open(path,'w') as f:json.dump(snap,f,ensure_ascii=False)
  r=subprocess.run([sys.executable,'hsml_chat.py','--load',path],input='บัว มี กลีบ ไหม\n',text=True,capture_output=True,timeout=30)
  checks['actual_restart']=r.returncode==0 and 'ใช่ บัว มี กลีบ' in r.stdout
 finally:os.remove(path)
 print('CHECKS '+json.dumps(checks,ensure_ascii=False))
 print('MALFORMED '+json.dumps(invalid))
 print('SYNTHETIC '+json.dumps({'query_commits':2000,'cache_cap':2,'cache_entries':2,
     'note':'knowledge/lexicon/subjects also grow; only interpretation cache is capped'}))
 print('CHECK PASS' if all(checks.values()) else 'CHECK FAIL')
 sys.exit(0 if all(checks.values()) else 1)
