#!/usr/bin/env python3
"""Independent finite transcript model across interpreter/GCC/x64/native seed."""
from pathlib import Path
import json,os,random,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT),HSROOT=str(ROOT))
rng=random.Random(719);code=['import std.console','s = std.console.create(5, 3)'];text='';history=[];count=0;want=''
for i in range(200):
    key=rng.choice(list('abcd 123')+['\x08','\n','\n','\t',None])
    literal='null'if key is None else json.dumps(key).replace('\\b','\x08')
    code.append('print std.console.feed(s, '+literal+')')
    submitted=key=='\n'
    if submitted:history=(history+[text])[-3:];text='';count+=1
    elif key=='\x08':text=text[:-1]
    elif key is not None and ' '<=key<='~'and len(text)<5:text+=key
    want+=str(submitted).lower()+'\n'+json.dumps([[text,False,5],history,3,count],separators=(', ',': '))+'\n'
    code.append('print json_str(s)')
for arg in ['0','17','true','1.5','"2"']:
    code+=['try:',f'  std.console.create(5, {arg})','except:','  print "rejected"'];want+='rejected\n'
passed=0
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);source=d/'state.holy';source.write_text('\n'.join(code)+'\n')
    for backend in ['interp','native','x64','native-hs']:
        if backend=='native-hs':
            exe=d/'program';r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),str(exe)],env=env,capture_output=True,text=True,timeout=90)
            if not r.returncode:r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=30)
        else:r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],env=env,capture_output=True,text=True,timeout=90)
        assert not r.returncode and r.stdout==want,(backend,r.returncode,r.stdout[-200:],want[-200:],r.stderr[-300:]);passed+=1
print(f'{passed}/{passed} bounded display-only console transcript gates (200 independent transitions)')
