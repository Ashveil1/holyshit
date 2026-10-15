import asm
for n in json_load(argv()[0]):
  asm.reset()
  asm.mov_tagged_int("rax", n)
  print json_str(asm.state()["code"])
