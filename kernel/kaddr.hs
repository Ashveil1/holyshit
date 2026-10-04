# kernel address spaces — one PML4 per space, kernel mappings shared.
#
# new() copies every present entry of the current PML4 into a fresh table, so
# the new space sees the same kernel (code, serial, heap) but can map its own
# user pages elsewhere. switch() loads it; a CR3 reload flushes the TLB, so
# no extra flush is needed. Helpers come before their users.
import kpage

# Address layout: PML4[0] (0 .. 512GB) is the shared kernel half — the boot
# identity map and everything the kernel maps itself. User pages must live in
# PML4 slots 1..511, i.e. at or above USER_MIN, so spaces stay isolated.
USER_MIN = 0x8000000000

def current():
  return cr3()

def new():
  # fresh PML4 sharing the current root's kernel mappings
  root = cr3()
  fresh = kpage.new_table()
  i = 0
  while i < 512:
    e = kpage.entry_get(root, i)
    if e & 1 != 0:
      kpage.entry_set(fresh, i, e)
    i = i + 1
  return fresh

def switch(pml4):
  set_cr3(pml4)
  return cr3() == pml4