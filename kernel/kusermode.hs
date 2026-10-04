# ring 3 end to end: load a real user ELF from a multiboot module, drop to
# ring 3 through the TSS, serve its syscalls from .hs, and come back when it
# exits.
import kmb
import kpmm
import kpage
import ksyscall
import kuser

fails = 0

def expect(label, got, want):
  global fails
  if got == want:
    print "ok", label
    return
  print "FAIL", label, got, want
  fails = fails + 1

expect("boot info found", kmb.usable(), true)
expect("one module", kmb.mods_count(), 1)
expect("pmm ready", kpmm.init() > 0, true)

# nothing loaded yet: entering ring 3 must not happen
expect("no handler yet", ksyscall.registered(), false)

loaded = kuser.load_module(0)
expect("user module loaded", loaded, 1)
expect("two segments", kuser.segments(), 2)
expect("text above the kernel half", kuser.text_base() >= ksyscall.USER_BIAS, true)
expect("entry mapped", kuser.entry() >= kuser.text_base(), true)
expect("entry in the text segment", kuser.entry() < kuser.text_end(), true)
expect("kernel half untouched", kpmm.busy(kuser.text_base()), true)

# the syscall path is live before we drop privileges
expect("handler registered", ksyscall.start(), true)
expect("registered", ksyscall.registered(), true)

# --- ring 3 ---
kuser.run()

expect("user stopped", ksyscall.user_stopped(), true)
expect("exit code", ksyscall.user_exit_code(), 0)
expect("syscalls served", ksyscall.calls() >= 8, true)
expect("last syscall was exit", ksyscall.last_syscall(), ksyscall.SYS_EXIT)
expect("user pages mapped", ksyscall.pages_mapped() > 16, true)

# the kernel is still ring 0 and still works
expect("kernel alive after ring 3", cr3() != 0, true)
expect("heap intact", kpmm.available() > 0, true)

print "fails", fails
print "kusermode-done"