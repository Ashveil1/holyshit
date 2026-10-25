#!/usr/bin/env python3
"""Fixed raw edit/history storage vs independent model and native kernel stress."""
from pathlib import Path
import json,os,random,shutil,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT)+':'+str(ROOT/'kernel')+':'+str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
code=['import kconsole_buffer','s = kconsole_buffer.create(7, 3)'];want='';text='';history=[];count=0;rng=random.Random(953)
for i in range(400):
    byte=rng.choice(list(range(97,106))+[None,8,8,10,10,0,9,31,127,255])
    code.append('print kconsole_buffer.feed(s, '+('null'if byte is None else str(byte))+')')
    submitted=byte==10
    if submitted:history=(history+[text])[-3:];text='';count+=1
    elif byte==8:text=text[:-1]
    elif byte is not None and 32<=byte<=126 and len(text)<7:text+=chr(byte)
    want+=str(submitted).lower()+'\n'+json.dumps([text,history,count],separators=(', ',': '))+'\n'
    code+=['recent = []','j = 0','while j < s[6]:','  append(recent, read_mem(kconsole_buffer.history_address(s,j), kconsole_buffer.history_length(s,j)))','  j = j + 1','print json_str([read_mem(s[0],s[3]), recent, s[7]])']
# Extremes, saturation, empty submissions, and wrapping at maximum retention.
code+=['small = kconsole_buffer.create(1,1)','kconsole_buffer.feed(small,97)','kconsole_buffer.feed(small,98)','print read_mem(small[0],small[3])','kconsole_buffer.feed(small,10)','kconsole_buffer.feed(small,10)','print small[6], kconsole_buffer.history_length(small,0)','large = kconsole_buffer.create(256,16)','j = 0','while j < 300:','  kconsole_buffer.feed(large,126)','  j = j + 1','print large[3]','j = 0','while j < 20:','  kconsole_buffer.feed(large,10)','  j = j + 1','print large[6], large[7], kconsole_buffer.history_length(large,0)']
want+='a\n1 0\n256\n16 20 0\n'
for cap,retained in [('0','3'),('257','3'),('true','3'),('1.5','3'),('"2"','3'),('7','0'),('7','17'),('7','false')]:
    code+=['try:',f'  kconsole_buffer.create({cap},{retained})','except:','  print "rejected"'];want+='rejected\n'
for byte in ['-1','256','true','1.5','"x"','[]']:
    code+=['try:',f'  kconsole_buffer.feed(s,{byte})','except:','  print "rejected"','print s[3], s[7]'];want+='rejected\n'+str(len(text))+' '+str(count)+'\n'
for index in ['-1','3','true','"0"']:
    code+=['try:',f'  kconsole_buffer.history_address(s,{index})','except:','  print "rejected"'];want+='rejected\n'
# Recall copies retained bytes into the edit without changing history/count.
for index, line in enumerate(history):
    code += [f'kconsole_buffer.recall(s,{index})',
             'print read_mem(s[0],s[3]), s[6], s[7]']
    want += line+' '+str(len(history))+' '+str(count)+'\n'
for index in ['-1','3','true','"0"']:
    code += ['try:',f'  kconsole_buffer.recall(s,{index})','except:',
             '  print "rejected"','print read_mem(s[0],s[3]), s[6], s[7]']
    want += 'rejected\n'+history[-1]+' '+str(len(history))+' '+str(count)+'\n'
code += ['empty = kconsole_buffer.create(7,3)','kconsole_buffer.feed(empty,97)',
         'try:','  kconsole_buffer.recall(empty,0)','except:','  print "rejected"',
         'print read_mem(empty[0],empty[3])',
         'kconsole_buffer.recall(large,15)','print large[3],large[6],large[7]',
         'kconsole_buffer.recall(small,0)','print small[3],small[6],small[7]']
want += 'rejected\na\n0 16 20\n0 1 2\n'
code += ['import kconsole_recall','nav = kconsole_recall.create(s)',
         'kconsole_buffer.reset(s)','kconsole_buffer.feed(s,120)',
         'print kconsole_recall.next(nav)',
         'print kconsole_recall.previous(nav)','print read_mem(s[0],s[3])',
         'print kconsole_recall.previous(nav)','print read_mem(s[0],s[3])',
         'print kconsole_recall.previous(nav)','print read_mem(s[0],s[3])',
         'print kconsole_recall.previous(nav)','print read_mem(s[0],s[3])',
         'print kconsole_recall.next(nav)','print read_mem(s[0],s[3])',
         'print kconsole_recall.next(nav)','print read_mem(s[0],s[3])',
         'print kconsole_recall.next(nav)','print read_mem(s[0],s[3])',
         'print kconsole_recall.next(nav)',
         'kconsole_recall.previous(nav)','kconsole_recall.detach(nav)',
         'kconsole_buffer.feed(s,121)','print read_mem(s[0],s[3])',
         'print kconsole_recall.next(nav)',
         'kconsole_recall.previous(nav)','kconsole_recall.next(nav)',
         'print read_mem(s[0],s[3])',
         'none = kconsole_buffer.create(1,1)','nnav = kconsole_recall.create(none)',
         'print kconsole_recall.previous(nnav), kconsole_recall.next(nnav)']
want += 'false\ntrue\n'+history[2]+'\ntrue\n'+history[1]+'\ntrue\n'+history[0]+'\nfalse\n'+history[0]+'\ntrue\n'+history[1]+'\ntrue\n'+history[2]+'\ntrue\nx\nfalse\ny\nfalse\ny\nfalse false\n'
code+=['kconsole_buffer.reset(s)','print s[3], s[6], s[7]'];want+='0 '+str(len(history))+' '+str(count)+'\n'
passed=0
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);source=d/'state.holy';source.write_text('\n'.join(code)+'\n')
    for backend in ['interp','native','x64','native-hs']:
        if backend=='native-hs':
            exe=d/'exe';r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),str(exe)],env=env,capture_output=True,text=True,timeout=120)
            assert not r.returncode,r.stderr[-400:]
            r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=30)
        else:r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],env=env,capture_output=True,text=True,timeout=120)
        assert not r.returncode and r.stdout==want,(backend,r.returncode,r.stdout[-250:],want[-250:],r.stderr[-400:]);passed+=1
    # Count real bump-allocation distance via two one-byte aligned raw markers.
    # No readkey/render/snapshot/log in the measured loop.
    source.write_text('import kconsole_buffer\nimport kconsole_recall\ndef mark():\n  unsafe:\n    return as_int(alloc(1))\ns = kconsole_buffer.create(42,4)\nbase = s[0]\nnav = kconsole_recall.create(s)\nbefore = mark()\ni = 0\nwhile i < 100000:\n  kconsole_buffer.feed(s,97)\n  kconsole_buffer.feed(s,98)\n  kconsole_buffer.feed(s,8)\n  kconsole_buffer.feed(s,99)\n  kconsole_buffer.feed(s,10)\n  kconsole_buffer.history_address(s,0)\n  kconsole_buffer.history_length(s,0)\n  kconsole_buffer.recall(s,0)\n  kconsole_buffer.feed(s,8)\n  kconsole_recall.previous(nav)\n  kconsole_recall.next(nav)\n  kconsole_recall.detach(nav)\n  kconsole_buffer.reset(s)\n  i = i + 1\nafter = mark()\nprint after - before\nprint s[0] == base, s[3], s[6], s[7]\nj = 0\nwhile j < 4:\n  print read_mem(kconsole_buffer.history_address(s,j), kconsole_buffer.history_length(s,j))\n  j = j + 1\nprint "FIXED CONSOLE DONE"\n')
    image=d/'image';r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(image)],env=env,capture_output=True,timeout=90);assert not r.returncode,r.stderr[-400:]
    driver=d/'driver';native=d/'native'
    build=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/kernel_ir.holy'),'-o',str(driver)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/kernel_ir.holy'),str(driver)])
    r=subprocess.run(build,env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-400:]
    r=subprocess.run([str(driver),str(source),str(native)],env=env,capture_output=True,timeout=90);assert not r.returncode and native.read_bytes()==image.read_bytes(),r.stderr[-400:];passed+=1
    qemu=os.environ.get('HS_TEST_QEMU')or shutil.which('qemu-system-x86_64')
    if qemu:
        serial=d/'serial';p=subprocess.Popen([qemu,'-kernel',str(image),'-serial','file:'+str(serial),'-display','none','-monitor','none','-nic','none'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            end=time.monotonic()+40;out=''
            while time.monotonic()<end:
                out=serial.read_text(errors='replace')if serial.exists()else ''
                if 'FIXED CONSOLE DONE\n'in out:break
                time.sleep(.1)
        finally:p.kill();p.wait()
        assert out=='16\ntrue 0 4 100000\nac\nac\nac\nac\nFIXED CONSOLE DONE\n',out[-400:];passed+=1
    else:print('skip fixed console QEMU stress: QEMU unavailable')
print(f'{passed}/{passed} fixed console gates (400 modeled transitions, kernel100000 submissions when QEMU available)')
