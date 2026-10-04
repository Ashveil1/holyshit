# cooperative tasks in ring 0 — policy in .hs, mechanism in the encoder.
#
# A task is a Func value f() plus a fresh stack. spawn() prepares both and
# queues the task; run() executes ready tasks round-robin until none remain.
# A running task gives control back with yield(), and must finish with
# exit(): returning from the entry without exit() reschedules a corpse that
# only bounces back to the scheduler (documented, not guarded).
#
# init order: kpmm.init() -> kheap.init(n) -> ktask.init(). The main task is
# not in the queue; run() drives everything from it. Helpers first (x64).
import kheap

STACK_SIZE = 16384
CTX_SIZE = 64

tctx = []
tstate = []
cur = -1
alive = 0
main_ctx = 0

def new_ctx():
  # zeroed 64-byte context block, returned tagged so safe code can hold it
  unsafe:
    Ptr m = alloc(64)
    I64 i = 0
    while i < 64:
      store8(m + i, 0)
      i = i + 1
    return as_int(m)

def init():
  global main_ctx
  main_ctx = new_ctx()
  return main_ctx != 0

def nspawned():
  return len(tctx)

def nalive():
  return alive

def current():
  return cur

def spawn(func):
  global alive
  stack = kheap.malloc(STACK_SIZE)
  if stack == 0:
    return -1
  top = (stack + STACK_SIZE) & ~15
  ctx = new_ctx()
  task_init(ctx, top, func)
  append(tctx, ctx)
  append(tstate, 1)
  alive = alive + 1
  return len(tctx) - 1

def next_ready(start):
  # next ready index at/after start (wraps), or -1
  n = len(tctx)
  if n == 0:
    return -1
  i = start
  checked = 0
  while checked < n:
    if i >= n:
      i = 0
    if tstate[i] == 1:
      return i
    i = i + 1
    checked = checked + 1
  return -1

def yield():
  global cur
  if cur < 0:
    return false
  me = cur
  nxt = next_ready(me + 1)
  if nxt < 0 or nxt == me:
    return false
  cur = nxt
  ctx_swap(tctx[me], tctx[nxt])
  cur = me
  return true

def exit():
  global alive, cur
  me = cur
  tstate[me] = 0
  alive = alive - 1
  cur = -1
  ctx_swap(tctx[me], main_ctx)

def run():
  global cur
  while alive > 0:
    nxt = next_ready(0)
    if nxt < 0:
      break
    cur = nxt
    task_run(main_ctx, tctx[nxt])
  cur = -1
  return alive