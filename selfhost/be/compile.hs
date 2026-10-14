# Hosted source -> ELF, output path in argv()[1].
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
g = be.GenIR(m, pyrt.py_os_path_dirname(srcpath))
img = g.build_ir_image()
outpath = argv()[1]
write_bytes(outpath, img)
