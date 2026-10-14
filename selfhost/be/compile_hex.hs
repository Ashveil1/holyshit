# Source -> ELF hex for the compiled compiler differential gate.
import parselib
import normalize
import irbuild
import verify
import be
import pyrt
parselib.P["wide_literals"] = true
srcpath = argv()[0]
m = irbuild.build_module(normalize.parse(read_text(srcpath)), "")
verify.verify_module(m)
g = be.GenIR(m, pyrt.py_os_path_dirname(srcpath), false)
img = g.build_ir_image()
HEX = "0123456789abcdef"
out = []
for b in img:
  append(out, HEX[b >> 4] + HEX[b & 15])
  if len(out) >= 4096:
    print join("", out)
    out = []
print join("", out)
