#!/usr/bin/env python3
"""Original label font: independent pixel oracle and differential execution."""
from pathlib import Path
import os,random,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
# Hand-drawn reference rows, independent of the module's packed table.
forms={'H':['#...#']*3+['#####']+['#...#']*3,
'I':['#####']+['..#..']*5+['#####'],
'A':['.###.','#...#','#...#','#####','#...#','#...#','#...#'],
'?':['.###.','#...#','....#','...#.','..#..','.....','..#..'],
' ':['.....']*7}
w,h=43,29;pixels=[7]*(w*h);rng=random.Random(907)
lines=['import std.font','s = std.gfx.surface(43, 29, 7)']
for i in range(22):
    text=rng.choice(['HI','Hi A','A\nI','@ H','?','']);scale=rng.randrange(1,5);x=rng.randrange(-25,50);y=rng.randrange(-25,35);color=90+i
    lines.append(f'std.font.draw(s, {x}, {y}, {text!r}, {color}, {scale})'.replace(repr(text),__import__('json').dumps(text)))
    cx,cy=x,y
    for ch in text:
        if ch=='\n':cx=x;cy+=8*scale;continue
        for row,bits in enumerate(forms.get(ch.upper(),forms['?'])):
            for col,bit in enumerate(bits):
                if bit=='#':
                    for dy in range(scale):
                        for dx in range(scale):
                            px,py=cx+col*scale+dx,cy+row*scale+dy
                            if 0<=px<w and 0<=py<h:pixels[py*w+px]=color
        cx+=6*scale
lines+=['print s[2]','print std.font.measure("", 1)','print std.font.measure("Hi\\nA", 2)','print std.font.measure("\\n", 1)','print std.font.glyph("h")','g = std.font.glyph("H")','g[0] = 0','print std.font.glyph("H")']
for ch,rows in forms.items():
    lines.append('print std.font.glyph('+__import__('json').dumps(ch)+')')
want=str(pixels)+'\n[0, 0]\n[24, 32]\n[0, 16]\n'+('[17, 17, 17, 31, 17, 17, 17]\n'*2)
for rows in forms.values():want+=str([int(row.replace('#','1').replace('.','0'),2) for row in rows])+'\n'
invalid=['std.font.draw(s, 0, 0, "A", 9, 0)','std.font.draw(s, 0, 0, "A", 9, 17)','std.font.draw(s, 0, 0, "A", 9, true)','std.font.draw(s, 0, 0, "A", 9, 1.5)','std.font.draw(s, 1048577, 0, "A", 9, 1)','std.font.draw(s, 0, 0, "A", true, 1)','std.font.draw(s, 0, 0, '+__import__('json').dumps('A'*1025)+', 9, 1)','std.font.draw(s, 0, 0, [], 9, 1)','std.font.glyph("")','std.font.glyph("HI")']
for call in invalid:lines+=['try:','  '+call,'except:','  print "rejected"'];want+='rejected\n'
lines+=['print s[2]'];want+=str(pixels)+'\n'
# Probe every supported character's shape and case mapping.
lines+=['for ch in std.font.characters:', '  bits = std.font.glyph(ch)','  if len(bits) != 7:', '    raise "bad glyph height"','  for row in bits:','    if row < 0 or row > 31:', '      raise "bad glyph width"','for i in range(26):','  upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[i]','  lower = "abcdefghijklmnopqrstuvwxyz"[i]','  if std.font.glyph(upper) != std.font.glyph(lower):','    raise "case mapping"','print "atlas ok"'];want+='atlas ok\n'
env=dict(os.environ,HSPATH=str(ROOT),HSROOT=str(ROOT));passed=failed=0
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);source=d/'font.holy';source.write_text('\n'.join(lines)+'\n')
    for backend in ['interp','native','x64','native-hs']:
        if backend=='native-hs':
            exe=d/'program';r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),str(exe)],env=env,capture_output=True,text=True,timeout=90)
            if not r.returncode:r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=30)
        else:r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],env=env,capture_output=True,text=True,timeout=90)
        ok=r.returncode==0 and r.stdout==want;passed+=ok;failed+=not ok
        if not ok:print('FAIL',backend,r.returncode,r.stdout[-200:],r.stderr[-300:])
    source.write_text('import std.font\ns = std.gfx.surface(16, 8, 0)\nstd.font.draw(s, 0, 0, "HI", 1, 1)\nprint "FONT", sum(s[2])\n')
    image=d/'kernel.elf';r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(image)],env=env,capture_output=True,text=True,timeout=60)
    ok=not r.returncode;passed+=ok;failed+=not ok
    if not ok:print('FAIL freestanding compile',r.stderr[-300:])
    qemu=shutil.which('qemu-system-x86_64')
    if qemu and ok:
        serial=d/'serial';p=subprocess.Popen([qemu,'-kernel',str(image),'-serial','file:'+str(serial),'-display','none','-monitor','none','-m','256M'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:p.wait(timeout=8)
        except subprocess.TimeoutExpired:p.kill();p.wait()
        ok=serial.exists() and 'FONT 32' in serial.read_text(errors='replace');passed+=ok;failed+=not ok
        if not ok:print('FAIL QEMU font sum')
    elif not qemu:print('skip QEMU font execution (unavailable)')
print(f'{passed}/{passed+failed} bitmap font gates (22 independent clipped/scaled labels)')
sys.exit(bool(failed))
