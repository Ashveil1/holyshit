import asm
import jitimage
import jitmem
extern:
  Ptr malloc(U64 n)
  U0 free(Ptr p)
  U0 qsort(Ptr base, U64 count, U64 size, Ptr compare)
# Two independently relocated code+data images must not alias.
def make_image(delta):
  asm.reset()
  asm.data_reset()
  asm.mov_rm("rax", "rdi", 0)
  asm.mov_rm("rcx", "rsi", 0)
  asm.sub_rr("rax", "rcx")
  asm.mov_rm_rip("rcx", "direction")
  asm.imul_rr("rax", "rcx")
  asm.ret()
  asm.data_label("direction")
  asm.data_qword(delta)
  return jitimage.publish()
x = make_image(1)
y = make_image(-1)
print x["ptr"]
print x["data"]
print y["ptr"]
print y["data"]
input()
a = malloc(24)
unsafe:
  Ptr p = as_ptr(a)
  store64(p, 30)
  store64(p + 8, 10)
  store64(p + 16, 20)
qsort(a, 3, 8, x["ptr"])
unsafe:
  print load64(p), load64(p + 8), load64(p + 16)
qsort(a, 3, 8, y["ptr"])
unsafe:
  print load64(p), load64(p + 8), load64(p + 16)
jitmem.release(x)
# The second mapping still works after releasing the first.
qsort(a, 3, 8, y["ptr"])
unsafe:
  print load64(p), load64(p + 8), load64(p + 16)
free(a)
jitmem.release(y)
print "released"
input()
