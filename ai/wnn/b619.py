"""Definition revision invalidates executed query interpretations."""
import json
from hsml_chat import fresh_chat
from b611 import stores

def case(restore,conflict=False):
 c=fresh_chat();c.attr['แมว'].add('หาง')
 c._commit('แมว มี หาง ไหม','ask_attr',('แมว','หาง'),'diagnostic')
 if conflict:
  c.user_turn('นิยาม แมว มี หาง ไหม เหมือน แมว มี หาง ไหม ตัวแปร 1,3')
  taught=c.user_turn('นิยาม แมว มี หาง ไหม เหมือน แมว เป็น หาง ไหม ตัวแปร 1,3')
 else:
  taught=c.user_turn('นิยาม แมว มี หาง ไหม เหมือน แมว มี หาง ตัวแปร 1,3')
 if restore:
  snap=c.snapshot();c=fresh_chat();c.restore(snap)
 b=stores(c);w=c.writes;a=c.write_attempts
 r=c.user_turn('แมว มี หาง ไหม')
 return {'restore':restore,'taught':taught,'reply':r,'conflict':conflict,'held':('ความหมายต่างกัน' in r if conflict else 'ตัดข้อความ' in r),
         'safe':stores(c)==b and c.writes==w and c.write_attempts==a and c.pending is None}
if __name__=='__main__':
 rows=[case(r,k) for r in [False,True] for k in [False,True]]
 print('RESULTS '+json.dumps(rows,ensure_ascii=False))
 print('CHECK PASS' if all(r['held'] and r['safe'] for r in rows) else 'CHECK FAIL')
