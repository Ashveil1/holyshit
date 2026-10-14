# Source -> multiboot kernel ELF via the maintained AST kernel backend.
import parselib
import normalize
import be
import pyrt
import asm
import klink
srcpath = argv()[0]
parselib.P["kernel_wide"] = true
parselib.P["wide_literals"] = true
prog = normalize.parse(read_text(srcpath))
g = be.Gen(prog, srcpath, true)
mod = {"name": "<main>", "prog": prog, "pfx": "", "scope": be.Gen_Scope(null, false), "dir": pyrt.py_os_path_dirname(srcpath)}
g.build_image(mod)
img = klink.link(asm.state(), g._stack_patch_pos)
H = "0123456789abcdef"
out = []
for b in img:
  append(out, H[b >> 4] + H[b & 15])
  if len(out) >= 4096:
    print join("", out)
    out = []
print join("", out)
