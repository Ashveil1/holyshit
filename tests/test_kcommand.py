#!/usr/bin/env python3
"""Bounded shared command API in a real kernel; native/reference image equality."""
from pathlib import Path
import os, shutil, subprocess, sys, tempfile, time
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=f'{ROOT}:{ROOT}/kernel:{ROOT}/selfhost:{ROOT}/selfhost/be',HSROOT=str(ROOT))
qemu=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip command kernel: QEMU unavailable');sys.exit(0)
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);source=d/'commands.holy'
    source.write_text('''import kcommand
import kconsole_buffer
def span(s):
  unsafe:
    return as_int(as_ptr(s)) + 16
def run(state, s, status, expected):
  assert kcommand.execute(state, span(s), len(s)) == status
  assert state[2] == len(expected)
  i = 0
  while i < len(expected):
    assert kcommand.byte(state[0], i) == kcommand.byte(span(expected), i)
    i = i + 1
c = kcommand.create(16)
run(c, "", 0, "")
run(c, "   ", 0, "")
run(c, "help", 1, "HELP ECHO")
run(c, "  help  ", 1, "HELP ECHO")
run(c, "echo", 2, "")
run(c, " echo  hello world  ", 2, "hello world")
run(c, "echo 1234567890123456", 2, "1234567890123456")
run(c, "echo 12345678901234567", 4, "1234567890123456")
unsafe:
  guarded_address = as_int(alloc(32))
g = [guarded_address,16,0,0]
past = guarded_address + 16
unsafe:
  store8(as_ptr(past), 90)
run(g, "echo 123456789012345678901234567890", 4, "1234567890123456")
assert kcommand.byte(past,0) == 90
run(c, "HELP", 3, "UNKNOWN COMMAND")
run(c, "help extra", 3, "UNKNOWN COMMAND")
run(c, "echoes hi", 3, "UNKNOWN COMMAND")
run(c, "echo a; reboot", 2, "a; reboot")
# Invalid input cannot publish a partial/new result.
for bad in ["echo bad\\n", "echo bad\\t"]:
  caught = false
  try:
    kcommand.execute(c, span(bad), len(bad))
  except:
    caught = true
  assert caught and c[3] == 2 and c[2] == 9
invalid = kconsole_buffer.create(16, 1)
kconsole_buffer.feed(invalid, 65)
p = invalid[0]
unsafe:
  store8(as_ptr(p), 0)
caught = false
try:
  kcommand.execute(c, p, 1)
except:
  caught = true
assert caught and c[3] == 2 and c[2] == 9
for n in [-1, 257]:
  caught = false
  try:
    kcommand.execute(c, span(""), n)
  except:
    caught = true
  assert caught
for capacity in [0, 15, 257]:
  caught = false
  try:
    kcommand.create(capacity)
  except:
    caught = true
  assert caught
# Same API on actual fixed-console input bytes, with history preserved.
s = kconsole_buffer.create(42, 4)
for b in [101,99,104,111,32,79,75]:
  kconsole_buffer.feed(s,b)
assert kcommand.execute(c,s[0],s[3]) == 2
assert c[2] == 2 and kcommand.byte(c[0],0) == 79 and kcommand.byte(c[0],1) == 75
assert kconsole_buffer.feed(s,10)
assert s[3] == 0 and s[6] == 1 and kconsole_buffer.history_length(s,0) == 7
print "COMMAND API DONE"
''')
    image=d/'kernel';native=d/'native';driver=d/'driver'
    subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(image)],env=env,capture_output=True,check=True,timeout=90)
    subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/kernel_ir.holy'),str(driver)],env=env,capture_output=True,check=True,timeout=240)
    subprocess.run([str(driver),str(source),str(native)],env=env,capture_output=True,check=True,timeout=90)
    assert image.read_bytes()==native.read_bytes(),'native/reference complete image mismatch'
    serial=d/'serial';p=subprocess.Popen([qemu,'-kernel',str(image),'-serial','file:'+str(serial),'-display','none','-monitor','none','-nic','none'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        deadline=time.monotonic()+30;out=''
        while time.monotonic()<deadline:
            out=serial.read_text(errors='replace') if serial.exists() else ''
            if 'COMMAND API DONE\n' in out or 'error:' in out:break
            time.sleep(.1)
        assert out=='COMMAND API DONE\n',out
    finally:p.kill();p.wait()
print('command API kernel gates passed (bounded cases, fixed input integration, native image equality)')
