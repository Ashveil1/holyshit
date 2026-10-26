"""Verification-only lossless definition persistence in standalone REPLs."""
import json,subprocess,sys

def run(lines,load=False):
    cmd=[sys.executable,'hsml_chat.py']
    if load:cmd+=['--load','logs/hsml_snapshot.json']
    return subprocess.run(cmd,input='\n'.join(lines)+'\n',text=True,
                          capture_output=True,check=True,timeout=30).stdout

if __name__=='__main__':
    first=run(['นิยาม วัว เป็น สัตว์เลี้ยง เหมือน วัว เป็น สัตว์เลี้ยง ตัวแปร 1,3','save'])
    second=run(['แพะเป็นสัตว์เลี้ยง','save'],True)
    snap=json.load(open('logs/hsml_snapshot.json'))
    before='สัตว์เลี้ยง' not in snap['isa'].get('แพะ',[])
    third=run(['แพะเป็นสัตว์เลี้ยง','ใช่','save'],True)
    snap2=json.load(open('logs/hsml_snapshot.json'))
    checks={'definition_saved':'จำรูปแบบใหม่แล้ว' in first,
            'restored_proposal_only':before and 'เดาว่า: สอนว่า แพะ เป็น สัตว์เลี้ยง ใช่ไหม' in second,
            'original_source_visible':'จากข้อความ «แพะ เป็น สัตว์เลี้ยง»' in second,
            'confirmed_fact_after_restart':'สัตว์เลี้ยง' in snap2['isa'].get('แพะ',[])}
    print('CHECKS '+json.dumps(checks,ensure_ascii=False))
    print('TRANSCRIPTS '+json.dumps([first,second,third],ensure_ascii=False))
    print('CHECK PASS' if all(checks.values()) else 'CHECK FAIL')
    sys.exit(0 if all(checks.values()) else 1)
