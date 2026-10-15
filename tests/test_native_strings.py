#!/usr/bin/env python3
"""Native UTF-8 literal and embedded-NUL display regression; exact raw bytes."""
from pathlib import Path
import os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT),HSROOT=str(ROOT))
src='''s = "a\\0b"
print s
print str(s)
print [s, [s], {s: s}]
print str([s, {s: [s]}])
print f"<{s}>"
print "ภาษาไทย สวัสดี", "café", "😀"
print "ÿ7", "é123", "🙂0"
print ["ไทย", {"é": "😀"}]
print str({"ไทย": ["é", s]})
print "prefix" + s + "suffix"
print join("\\0", ["x", "y"])
d = {"a\\0b": 1, "a\\0c": 2}
print len(d), d["a\\0b"], d["a\\0c"], has(d, "a")
print keys(d)
print json_str(d)
'''
want=(b'a\0b\na\0b\n[a\0b, [a\0b], {a\0b: a\0b}]\n'
      b'[a\0b, {a\0b: [a\0b]}]\n<a\0b>\n'+
      'ภาษาไทย สวัสดี café 😀\nÿ7 é123 🙂0\n[ไทย, {é: 😀}]\n{ไทย: [é, a\0b]}\nprefixa\0bsuffix\nx\0y\n2 1 2 false\n[a\0b, a\0c]\n{"a\\u0000b": 1, "a\\u0000c": 2}\n'.encode())
passed=failed=0
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);source=d/'strings.hs';source.write_text(src)
    for backend in ['interp','native','x64','native-hs']:
        if backend=='native-hs':
            exe=d/'program';r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),str(exe)],env=env,capture_output=True,timeout=90)
            if not r.returncode:r=subprocess.run([str(exe)],capture_output=True,timeout=30)
        else:r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],env=env,capture_output=True,timeout=90)
        ok=not r.returncode and r.stdout==want;passed+=ok;failed+=not ok
        if not ok:print('FAIL',backend,r.returncode,repr(r.stdout),repr(r.stderr[-300:]))
print(f'{passed}/{passed+failed} raw string display gates (UTF-8, NUL, nested values, interpolation)')
sys.exit(bool(failed))
