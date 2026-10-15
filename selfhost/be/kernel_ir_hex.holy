# Source -> multiboot kernel ELF via the IR kernel backend.
import parselib
import normalize
import irbuild
import verify
import be
import pyrt
import asm
import klink
srcpath = argv()[0]
parselib.P["kernel_wide"] = true
parselib.P["wide_literals"] = true
prog = normalize.parse(read_text(srcpath))
m = irbuild.build_module(prog, "")
verify.verify_module(m)
g = be.GenIR(m, pyrt.py_os_path_dirname(srcpath), true)
g.build_kernel_image()
img = klink.link(asm.state(), g._stack_patch_pos)
H = "0123456789abcdef"
out = []
for b in img:
  append(out, H[b >> 4] + H[b & 15])
  if len(out) >= 4096:
    print join("", out)
    out = []
print join("", out)
