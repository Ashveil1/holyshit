#!/usr/bin/env python3
"""Bounded cold split/join over text and flat Lists with cumulative byte accounting."""
from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT));passed=0
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);driver=d/'driver'
    def build(source,output):
        command=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(source),'-o',str(output)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),str(output)])
        r=subprocess.run(command,env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-400:]
    build(ROOT/'selfhost/be/cold_scalar_run.holy',driver);passed+=1
    cases=[
      's = "a,b,,c"\nparts = split(s, ",")\nprint len(parts)\nprint parts[0]\nprint parts[2]\nfor p in parts:\n  print p\n',
      'words = split("  the quick  brown fox ")\nprint len(words)\nprint words[0] + "-" + words[3]\nprint len(split(""))\nprint len(split("", ","))\nprint split("", ",")[0] + "!"\n',
      's = "a,b,c"\nprint s.split(",")[1]\nprint "x-y".split("-")[0]\nt = "  spaced out "\nprint t.split()[1]\n',
      'parts = ["a", "b", "c"]\nprint join("-", parts)\nprint join("", ["a", "b"])\nprint join("XYZ", ["a"])\nprint join("-", [])\n',
      'print join("+", split("one two", " "))\ndef csv(line):\n  return join(";", split(line, ","))\nprint csv("x,y,z")\ndef fields(line):\n  return split(line, ",")\nfs = fields("p,q")\nprint fs[1]\n',
      'xs = split("a b c", " ")\nprint "b" in xs\nprint "z" not in xs\ns = "key:value"\npair = split(s, ":")\nprint pair[0][0:1]\nprint pair[1][0:]\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,reason,before in [
      ('print split([1])\n','split wants split(s) or split(s, sep)',b''),
      ('print split("a", 1)\n','split wants split(s) or split(s, sep)',b''),
      ('print split("a", "b", "c")\n','split wants split(s) or split(s, sep)',b''),
      ('print join(1, ["a"])\n','join wants join(sep, list)',b''),
      ('print join("-", [1, "a"])\n','join needs a list of Str',b''),
      ('print split("ab", "")\n','empty separator',b''),
      ('print ["a"].join("-")\n','join wants join(sep, list)',b''),
      ('s = '+json.dumps('x'*1024)+'\ni = 0\nwhile i < 62:\n  u = s[0:1024]\n  i = i + 1\nparts = split(s, ",")\nparts = split(s, ",")\nprint "done"\n','text byte budget',b''),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold split/join gates (no shared native values or hot tier)')
