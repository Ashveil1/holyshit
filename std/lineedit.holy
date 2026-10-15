# Bounded ASCII line state for early keyboard consoles, no hardware access.
def create(capacity):
  capacity = capacity | 0
  if capacity < 1 or capacity > 256:
    raise "line capacity must be 1..256"
  return ["", false, capacity]
def reset(state):
  state[0] = ""
  state[1] = false
def byte_address():
  unsafe:
    Ptr p = alloc(1)
    store8(p, 8)
    return as_int(p)
backspace_key = read_mem(byte_address(), 1)
def feed(state, key):
  if key == null:
    return
  key = key + ""
  if len(key) != 1:
    raise "line key requires one character"
  if state[1]:
    return
  if key == "\n":
    state[1] = true
  elif key == backspace_key:
    if len(state[0]) > 0:
      state[0] = state[0][0:len(state[0]) - 1]
  elif key >= " " and key <= "~":
    if len(state[0]) < state[2]:
      state[0] = state[0] + key
