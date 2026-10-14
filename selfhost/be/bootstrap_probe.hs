# Source -> ELF hex for the compiled compiler differential gate.
import normalize
import irbuild
import verify
import be
import pyrt
srcpath = argv()[0]
print "start"
prog = normalize.parse(read_text(srcpath))
print "parsed"
m = irbuild.build_module(prog, "")
print "lowered"
verify.verify_module(m)
print "verified"
g = be.GenIR(m, pyrt.py_os_path_dirname(srcpath))
print "planned"
img = g.build_ir_image()
print "image"
HEX = "0123456789abcdef"
out = []
for b in img:
  append(out, HEX[b >> 4] + HEX[b & 15])
  if len(out) >= 4096:
    print join("", out)
    out = []
print join("", out)
