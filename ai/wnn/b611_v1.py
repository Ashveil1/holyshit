"""B611: adversarial path coverage, no expectation changes after run."""
import json
import b562 as B
from hsml_chat import fresh_chat
from b570 import Watchdog,BUDGET

def stores(c):
    return ({k:sorted(v) for k,v in c.isa.items()},
            {k:sorted(v) for k,v in c.attr.items()})

def force(c,s,d='teach_isa'):
    for _ in range(100): c.m.add(B.encode(s),d)
    p,mg=B.predict(c.m,B.encode(s),-1e18)
    assert p==d and mg>=c.tau_hi,(p,mg,c.tau_hi)
    return {'prediction':p,'margin':mg,'threshold':c.tau_hi}

def probe(c,s):
    before=stores(c); w=c.writes; attempts=c.write_attempts
    r=c.user_turn(s)
    return {'surface':s,'reply':r,'store_unchanged':stores(c)==before,
            'write_delta':c.writes-w,'attempt_delta':c.write_attempts-attempts,
            'statement_proposal':bool(c.pending and c.pending.get('intent') in {'teach_isa','teach_attr','retract_attr'})}

if __name__=='__main__':
    watch=Watchdog(BUDGET);watch.start()
    rows={}
    quote='เขา บอก วัว เป็น สัตว์เลี้ยง'
    for name,s in [('quoted',quote),('unk','<UNK:เมื่อวาน> วัว เป็น สัตว์เลี้ยง'),
                   ('question','วัว เป็น สัตว์เลี้ยง ไหม')]:
        c=fresh_chat(); ranking=force(c,s)
        rows[name]={'ranking':ranking,**probe(c,s)}
        rows[name+'_repeat']=probe(c,s)
        c=fresh_chat();force(c,s);snap=c.snapshot()
        restored=fresh_chat();restored.restore(snap)
        rows[name+'_restored']=probe(restored,s)
    c=fresh_chat();force(c,quote)
    c._unparsed=lambda s,sl:[]
    rows['bypass_diagnostic']=probe(c,quote)
    c=fresh_chat()
    r=c.user_turn('นิยาม วัว เป็น สัตว์เลี้ยง ไหม เหมือน วัว เป็น สัตว์เลี้ยง ตัวแปร 1,3')
    assert len(c.defs)==1,r
    force(c,'แพะ เป็น สัตว์เลี้ยง')
    rows['definition_drops_question_marker']=probe(c,'แพะ เป็น สัตว์เลี้ยง ไหม')
    snap=c.snapshot();d=fresh_chat();d.restore(snap)
    rows['definition_restored']=probe(d,'ควาย เป็น สัตว์เลี้ยง ไหม')
    negatives=[v for k,v in rows.items() if k!='bypass_diagnostic']
    ok=all(v['store_unchanged'] and v['write_delta']==0 and v['attempt_delta']==0 and not v['statement_proposal'] for v in negatives)
    bypass=rows['bypass_diagnostic']['write_delta']>0
    watch.stop()
    print('RESULTS '+json.dumps(rows,ensure_ascii=False))
    print('RES '+json.dumps({'peak_rss_bytes':watch.peak}))
    print('CHECK PASS' if ok and bypass else 'CHECK FAIL')
