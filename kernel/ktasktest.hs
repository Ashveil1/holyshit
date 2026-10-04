# cooperative tasks on bare metal: three tasks interleave by yielding,
# share a counter, exit cleanly, and control returns to main
import kmb
import kpmm
import kheap
import ktask

fails = 0

def expect(label, got, want):
  global fails
  if got == want:
    print "ok", label
    return
  print "FAIL", label, got, want
  fails = fails + 1

count = 0

def bump(n):
  global count
  count = count + n
  print "task added", n, "total", count
  ktask.yield()
  print "task resumed, total", count

def worker_a():
  print "a start"
  bump(1)
  bump(10)
  print "a exit"
  ktask.exit()

def worker_b():
  print "b start"
  bump(100)
  print "b exit"
  ktask.exit()

def worker_c():
  print "c start"
  ktask.yield()
  print "c middle"
  ktask.yield()
  print "c exit"
  ktask.exit()

expect("boot info found", kmb.usable(), true)
expect("pmm ready", kpmm.init() > 0, true)
expect("heap ready", kheap.init(64), true)
expect("tasks ready", ktask.init(), true)
expect("no tasks yet", ktask.nspawned(), 0)

ia = ktask.spawn(worker_a)
expect("spawn a", ia, 0)
ib = ktask.spawn(worker_b)
expect("spawn b", ib, 1)
ic = ktask.spawn(worker_c)
expect("spawn c", ic, 2)
expect("three alive", ktask.nalive(), 3)

expect("run to completion", ktask.run(), 0)
expect("none alive", ktask.nalive(), 0)
expect("counter total", count, 111)
expect("back in main", ktask.current(), -1)

print "fails", fails
print "ktask-done"