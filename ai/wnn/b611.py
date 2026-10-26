"""B611: adversarial path coverage, no expectation changes after run."""
import json, subprocess, sys, tempfile, os
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
    def add_def(c, text):
        r=c.user_turn(text)
        assert r=='จำรูปแบบใหม่แล้ว',r

    for name,definition,surface in [
        ('definition_quote', 'นิยาม เขา บอก วัว เป็น สัตว์เลี้ยง เหมือน วัว เป็น สัตว์เลี้ยง ตัวแปร 3,5',
         'เขา บอก แพะ เป็น สัตว์เลี้ยง'),
        ('definition_unk', 'นิยาม <UNK:เมื่อวาน> วัว เป็น สัตว์เลี้ยง เหมือน วัว เป็น สัตว์เลี้ยง ตัวแปร 2,4',
         '<UNK:เมื่อวาน> แพะ เป็น สัตว์เลี้ยง')]:
        c=fresh_chat();add_def(c,definition);force(c,'แพะ เป็น สัตว์เลี้ยง')
        rows[name]=probe(c,surface)
        d=fresh_chat();d.restore(c.snapshot());rows[name+'_restored']=probe(d,surface)
    c=fresh_chat()
    add_def(c,'นิยาม วัว เป็น สัตว์เลี้ยง เหมือน วัว เป็น สัตว์เลี้ยง ตัวแปร 1,3')
    add_def(c,'นิยาม วัว เป็น สัตว์เลี้ยง เหมือน วัว มี สัตว์เลี้ยง ตัวแปร 1,3')
    rows['overlapping_incompatible']=probe(c,'แพะ เป็น สัตว์เลี้ยง')
    c=fresh_chat()
    add_def(c,'นิยาม วัว น่ะ เป็น สัตว์เลี้ยง เหมือน วัว เป็น สัตว์เลี้ยง ตัวแปร 1,4')
    add_def(c,'นิยาม วัว เป็น สัตว์เลี้ยง เหมือน วัว มี สัตว์เลี้ยง ตัวแปร 1,3')
    rows['nested_lossy_hold']=probe(c,'แพะ น่ะ เป็น สัตว์เลี้ยง')
    c=fresh_chat()
    add_def(c,'นิยาม วัว เป็น สัตว์เลี้ยง เหมือน วัว เป็น สัตว์เลี้ยง ตัวแปร 1,3')
    add_def(c,'นิยาม แพะ เป็น สัตว์ป่า เหมือน แพะ เป็น สัตว์ป่า ตัวแปร 1,3')
    force(c,'ควาย เป็น สัตว์เลี้ยง')
    rows['equivalent_overlaps_propose']=probe(c,'ควาย เป็น สัตว์เลี้ยง')
    provenance=c.pending.get('provenance') if c.pending else None
    assert provenance and provenance['original']=='ควาย เป็น สัตว์เลี้ยง'
    before=c.writes;attempts=c.write_attempts
    accepted=c.user_turn('ใช่')
    positive={'reply':accepted,'write_delta':c.writes-before,
              'attempt_delta':c.write_attempts-attempts,
              'fact_present':'สัตว์เลี้ยง' in c.isa.get('ควาย',set())}
    assert positive['write_delta']==positive['attempt_delta']==1 and positive['fact_present']
    # Direct repeated _commit diagnostic proves set equality cannot mask counters.
    before=stores(c);w=c.writes;a=c.write_attempts
    c._commit('ควาย เป็น สัตว์เลี้ยง','teach_isa',('ควาย','สัตว์เลี้ยง'),'diagnostic')
    counter_diagnostic={'store_unchanged':stores(c)==before,
                        'write_delta':c.writes-w,'attempt_delta':c.write_attempts-a}
    assert counter_diagnostic=={'store_unchanged':True,'write_delta':1,'attempt_delta':1}
    # Independent interpreter loads persisted definition+mapper state.
    c=fresh_chat()
    add_def(c,'นิยาม วัว เป็น สัตว์เลี้ยง ไหม เหมือน วัว เป็น สัตว์เลี้ยง ตัวแปร 1,3')
    force(c,'แพะ เป็น สัตว์เลี้ยง')
    fd,path=tempfile.mkstemp(suffix='.json',dir='logs');os.close(fd)
    try:
        with open(path,'w') as f:json.dump(c.snapshot(),f,ensure_ascii=False)
        code="from b611 import probe; from hsml_chat import fresh_chat; import json,sys; c=fresh_chat(); c.restore(json.load(open(sys.argv[1]))); print(json.dumps(probe(c,'แพะ เป็น สัตว์เลี้ยง ไหม'),ensure_ascii=False))"
        child=subprocess.run([sys.executable,'-c',code,path],capture_output=True,text=True,check=True,timeout=30)
        rows['standalone_restore']=json.loads(child.stdout)
    finally:os.remove(path)
    negatives=[v for k,v in rows.items() if k not in {'bypass_diagnostic','equivalent_overlaps_propose'}]
    ok=all(v['store_unchanged'] and v['write_delta']==0 and v['attempt_delta']==0 and not v['statement_proposal'] for v in negatives)
    eq=rows['equivalent_overlaps_propose']
    ok=ok and eq['store_unchanged'] and eq['write_delta']==eq['attempt_delta']==0
    bypass=rows['bypass_diagnostic']['write_delta']>0
    watch.stop()
    print('RESULTS '+json.dumps(rows,ensure_ascii=False))
    print('POSITIVE '+json.dumps(positive,ensure_ascii=False))
    print('COUNTER-DIAGNOSTIC '+json.dumps(counter_diagnostic))
    print('RES '+json.dumps({'peak_rss_bytes':watch.peak}))
    print('CHECK PASS' if ok and bypass else 'CHECK FAIL')
