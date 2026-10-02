print "before-de"
unsafe:
  asm("mov $1, %eax; xor %ecx, %ecx; div %ecx")
print "after-de"
