# Source -> ELF hex for the compiled compiler differential gate.
import normalize
import irbuild
import verify
import be
import pyrt
srcpath = argv()[0]
m = irbuild.build_module(normalize.parse(read_text(srcpath)), "")
verify.verify_module(m)
g = be.GenIR(m, pyrt.py_os_path_dirname(srcpath))
img = g.build_ir_image()
HEX = "0123456789abcdef"
out = ""
for b in img:
  out = out + HEX[b >> 4] + HEX[b & 15]
print out
