# Experimental eager in-process compilation. The emitted _start exits the
# process, so the compiler driver never resumes and the OS owns final cleanup.
import parselib
import normalize
import irbuild
import verify
import be
import pyrt
import asm
import jitimage
import jitbind
def prepare():
  parselib.P["wide_literals"] = true
  srcpath = argv()[0]
  m = irbuild.build_module(normalize.parse(read_text(srcpath)), "")
  verify.verify_module(m)
  g = be.GenIR(m, pyrt.py_os_path_dirname(srcpath), false)
  sections = g.build_ir_extern_sections()
  handles = jitbind.bind(g.ffi_libs, g.ffi_syms, g.ffi_owners, pyrt.py_os_path_dirname(srcpath))
  # Forward arguments and the Linux process environment through an initial
  # stack frame. Addresses are formed at runtime, after RIP-relative relocation.
  args = argv()
  entries = ["hs-jit"] + args[1:len(args)]
  argc = len(entries)
  rawenv = read_text("/proc/self/environ")
  for value in split(rawenv, "\0"):
    if len(value) > 0:
      append(entries, value)
  entry = len(asm.state()["code"])
  slots = len(entries) + 3
  if slots % 2 == 0:
    slots = slots + 1
  asm.sub_ri32("rsp", slots * 8)
  asm.mov_ri32("rax", argc)
  asm.mov_mr("rsp", "rax", 0)
  position = 1
  for i in range(len(entries)):
    if i == argc:
      asm.mov_ri32("rax", 0)
      asm.mov_mr("rsp", "rax", position * 8)
      position = position + 1
    label = "jit_arg_" + str(i)
    asm.data_label(label)
    asm.data_bytes(pyrt.py_encode(entries[i], "utf-8"))
    asm.data_bytes([0])
    asm.lea_rip("rax", label)
    asm.mov_mr("rsp", "rax", position * 8)
    position = position + 1
  asm.mov_ri32("rax", 0)
  asm.mov_mr("rsp", "rax", position * 8)
  if len(entries) == argc:
    asm.mov_mr("rsp", "rax", (position + 1) * 8)
  asm.jmp("_start")
  image = jitimage.publish()
  pointer = image["ptr"] + entry
  return pointer
try:
  pointer = prepare()
except as e:
  print pyrt.py_estr(e)
  raise "jit compilation failed"
unsafe:
  I64 result = call0(as_ptr(pointer))
