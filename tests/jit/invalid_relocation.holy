import asm
import jitmem
import jitimage
saved = {"ptr": 0}
def invalid_reloc(text, data):
  saved["ptr"] = text
  return [1, 2]
try:
  jitmem.publish_sections([195], [0], invalid_reloc)
except:
  print "size mismatch rejected"
print saved["ptr"]
input()
asm.reset()
asm.data_reset()
asm.lea_rip("rax", "data")
asm.data_label("data")
asm.data_qword(0)
try:
  jitimage.relocate(0, 2147483655)
except:
  print "out of range rejected"
