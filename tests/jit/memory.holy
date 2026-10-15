import jitmem
import asm
extern:
  Ptr malloc(U64 n)
  U0 free(Ptr p)
  U0 qsort(Ptr base, U64 count, U64 size, Ptr compare)
# Generate a real C ABI comparator: return *left - *right.
asm.reset()
asm.mov_rm("rax", "rdi", 0)
asm.mov_rm("rcx", "rsi", 0)
asm.sub_rr("rax", "rcx")
asm.ret()
image = jitmem.publish(asm.resolve_at(0, 0))
ptr = image["ptr"]
print ptr
print image["size"]
# Let the test inspect /proc/PID/maps before execution.
input()
a = malloc(24)
unsafe:
  Ptr p = as_ptr(a)
  store64(p, 30)
  store64(p + 8, 10)
  store64(p + 16, 20)
qsort(a, 3, 8, ptr)
unsafe:
  print load64(p), load64(p + 8), load64(p + 16)
free(a)
jitmem.release(image)
print image["ptr"], image["live"]
input()
try:
  jitmem.release(image)
except:
  print "double release rejected"
