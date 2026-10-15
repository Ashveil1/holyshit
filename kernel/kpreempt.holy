# preemption on bare metal: hog tasks that never yield must still be
# force-switched by quantum expiry. Each hog busy-waits K ticks (measured by
# the very clock that preempts it), so every task is guaranteed to span
# several quanta no matter how fast the host runs: with quantum 1, each of
# those ticks switches away from whoever runs. A shared counter would race
# by design (no locks yet), so every task counts privately and exactly.
# All reporting happens with preemption off so serial lines stay whole.
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

KWAIT = 5

c0 = 0
c1 = 0
c2 = 0

def hog0():
  global c0
  s = ticks()
  while ticks() - s < KWAIT:
    c0 = c0 + 1
  ktask.exit()

def hog1():
  global c1
  s = ticks()
  while ticks() - s < KWAIT:
    c1 = c1 + 1
  ktask.exit()

def hog2():
  global c2
  s = ticks()
  while ticks() - s < KWAIT:
    c2 = c2 + 1
  ktask.exit()

expect("boot info found", kmb.usable(), true)
expect("pmm ready", kpmm.init() > 0, true)
expect("heap ready", kheap.init(64), true)
expect("tasks ready", ktask.init(), true)
expect("spawn 0", ktask.spawn(hog0), 0)
expect("spawn 1", ktask.spawn(hog1), 1)
expect("spawn 2", ktask.spawn(hog2), 2)
expect("preempt on", ktask.preempt_on(), true)
expect("run to completion", ktask.run(), 0)
expect("preempt off", ktask.preempt_off(), true)
expect("none alive", ktask.nalive(), 0)
expect("hog0 counted", c0 > 1000, true)
expect("hog1 counted", c1 > 1000, true)
expect("hog2 counted", c2 > 1000, true)
expect("hog0 was preempted", ktask.npreempted(0) > 0, true)
expect("hog1 was preempted", ktask.npreempted(1) > 0, true)
expect("hog2 was preempted", ktask.npreempted(2) > 0, true)

print "fails", fails
print "kpreempt-done"