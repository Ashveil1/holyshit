# irx64_run.hs: IR text -> hosted x64 image through the hs backend (be.hs),
# printed as hex (tests/test_be.py compares with irx64.py).
import be
import irlib

HEX = "0123456789abcdef"
text = read_text(argv()[0])
m = irlib.parse(text)
g = be.GenIR(m, ".")
img = g.build_ir_image()
out = ""
for b in img:
  out = out + HEX[b >> 4] + HEX[b & 15]
print out
