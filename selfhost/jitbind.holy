# Resolve the generated GOT before publishing any executable target code.
# Handles deliberately stay open until process exit: _start never returns.
import asm
extern:
  Ptr dlopen(Str path, I64 flags)
  Ptr dlsym(Ptr handle, Str name)
def bind(libraries, symbols, owners, basedir):
  handles = []
  if len(symbols) == 0:
    return handles
  bypath = {}
  for path in ["libc.so.6"] + libraries:
    resolved = path
    if "/" in path and path[0:1] != "/":
      resolved = basedir + "/" + path
    handle = dlopen(resolved, 258)
    if handle == 0:
      raise "jit: cannot load library " + path
    append(handles, handle)
    bypath[path] = handle
  offset = asm.state()["data_labels"]["ffi_got_"]
  for name in symbols:
    owner = owners[name] if name in owners else "libc.so.6"
    pointer = dlsym(bypath[owner], name)
    if pointer == 0:
      raise "jit: unknown extern symbol " + name
    for i in range(8):
      asm.state()["data"][offset + i] = (pointer >> (8 * i)) & 255
    offset = offset + 8
  return handles
