# Resolve the generated GOT before publishing any executable target code.
# Handles deliberately stay open until process exit: _start never returns.
import asm
extern:
  Ptr dlopen(Str path, I64 flags)
  Ptr dlsym(Ptr handle, Str name)
def bind(libraries, symbols):
  handles = []
  if len(symbols) == 0:
    return handles
  for path in ["libc.so.6"] + libraries:
    handle = dlopen(path, 258)
    if handle == 0:
      raise "jit: cannot load library " + path
    append(handles, handle)
  offset = asm.state()["data_labels"]["ffi_got_"]
  for name in symbols:
    pointer = 0
    for handle in handles:
      if pointer == 0:
        pointer = dlsym(handle, name)
    if pointer == 0:
      raise "jit: unknown extern symbol " + name
    for i in range(8):
      asm.state()["data"][offset + i] = (pointer >> (8 * i)) & 255
    offset = offset + 8
  return handles
