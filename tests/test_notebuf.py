#!/usr/bin/env python3
"""Bounded cursor editing: movement, insertion, reflow, canaries and cap."""
import contextlib, io, os, platform, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from x64gen import build_x64, build_x64_ast
runner=[]
if platform.machine() not in ('x86_64','amd64'):
    qemu=shutil.which('qemu-x86_64')
    if not qemu:
        print('skip hosted x86 note buffer test: qemu-x86_64 unavailable');sys.exit(0)
    runner=[qemu]
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp)
    for name,build in [('ir',build_x64),('ast',build_x64_ast)]:
        image=d/name
        with contextlib.redirect_stdout(io.StringIO()):
            rc=build(str(ROOT/'kernel/unotebuftest.holy'),str(image))
        assert not rc
        r=subprocess.run(runner+[str(image)],capture_output=True,text=True,timeout=20)
        assert r.returncode==0 and '\nfails 0\n' in r.stdout and 'notebuf-done\n' in r.stdout,(name,r)
        assert r.stdout.count('ok ')==45,r.stdout
        print('ok bounded note buffers',name)
print('2/2 cursor note buffer gates')

# Independent Python reference: scan characters into visual caret stops,
# then compare every byte/caret after deterministic mixed editing streams.
import ast, random
rng = random.Random(1407)
keys = [97]*96 + [130]*40 + [8,98,10,134,128,129,132,133]*8
for _ in range(220):
    keys.append(rng.choice([97,98,104,105,10,8,128,129,130,131,132,133,134,135,-1]))

def stops(text):
    row = col = 0; positions = []
    for ch in text:
        if ch != 10 and col == 32:
            row += 1; col = 0
        positions.append((row,col))
        if ch == 10: row += 1; col = 0
        else: col += 1
    positions.append((row,col))
    return positions

text = []; caret = 0; want = []
for key in keys:
    ps = stops(text); row,col = ps[caret]
    if key == -1: text=[]; caret=0
    elif key == 130: caret=max(0,caret-1)
    elif key == 131: caret=min(len(text),caret+1)
    elif key in (128,129):
        target=row+(-1 if key==128 else 1)
        options=[i for i,p in enumerate(ps) if p[0]==target]
        if options:caret=min(options,key=lambda i:abs(ps[i][1]-col))
    elif key in (132,133):
        options=[i for i,p in enumerate(ps) if p[0]==row]
        caret=options[0 if key==132 else -1]
    elif key==8 and caret:
        del text[caret-1];caret-=1
    elif key==134 and caret<len(text):del text[caret]
    elif key==10 or 32<=key<=126:
        candidate=text[:caret]+[key]+text[caret:]
        if len(candidate)<=98 and stops(candidate)[-1][0]<3:
            text=candidate;caret+=1
    where=stops(text)[caret]
    display=[];column=0
    for ch in text:
        if ch != 10 and column==32:
            display.append(10);column=0
        display.append(ch)
        column=0 if ch==10 else column+1
    want.append([text.copy(),caret,list(where),display])
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);source=d/'sequence.holy'
    shutil.copyfile(ROOT/'kernel/unotebuf.holy', d/'unotebuf.holy')
    source.write_text('import unotebuf\ndef address(text):\n  unsafe:\n    return as_int(as_ptr(text)) + 16\nnote = unotebuf.create()\nkeys = '+str(keys)+'\n'
        'for key in keys:\n  if key == -1:\n    unotebuf.clear(note)\n  else:\n    unotebuf.edit(note, key)\n'
        '  bytes = []\n  for i in range(note[2]):\n    append(bytes, unotebuf.byte_at(note[1] + i))\n'
        '  display = unotebuf.rendered(note)\n  rendered = []\n  for i in range(byte_len(display)):\n    append(rendered, unotebuf.byte_at(address(display) + i))\n'
        '  print [bytes, note[3], unotebuf.position(note), rendered]\n')
    for name,build in [('ir',build_x64),('ast',build_x64_ast)]:
        image=d/name
        with contextlib.redirect_stdout(io.StringIO()):rc=build(str(source),str(image))
        assert not rc
        r=subprocess.run(runner+[str(image)],capture_output=True,text=True,timeout=30)
        assert r.returncode==0,(name,r.stderr,r.stdout[-500:])
        got=[ast.literal_eval(line) for line in r.stdout.splitlines()]
        assert got==want,(name,next(((i,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b),None))
        print('ok independent editor state oracle',name,len(want),'edits')
print('2/2 independent randomized editor-oracle gates')
