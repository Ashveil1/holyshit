# Private-root bounded ELF integration

`klowelf.holy` connects a small static ELF loader with the private page-table
experiment. It does not change `kuser`, `ksyscall` or the high-address
`klinux` personality. It is a one-program, one-run kernel-internal experiment.

An ELF64 little-endian x86-64 ET_EXEC may have at most eight program headers
and 16 MiB of segment pages. Only PT_LOAD, PT_NULL and ignored PT_GNU_STACK
are accepted. Segments must fit the existing 256-512 MiB virtual window,
excluding its final two pages reserved for the stack and gap. No interpreter,
dynamic sections, relocation or TLS support is implied. Page-aligned segment
ranges cannot overlap; file and header bounds are checked before reads.
Only R, RX and RW flags are accepted, with entry in executable file bytes.

Loading happens while the boot root remains active. Each new user frame is
zeroed, then file bytes are copied through its physical identity alias.
Read-only code/data leaves are protected in the cloned root. A zeroed stack
page is mapped separately. On run, the kernel switches CR3, installs the
small write/exit handler, enters ring 3 and restores the prior root and
normal Holyshit handler after exit. Startup vectors are explicitly empty in
this first integration, not the richer `klinux.run_with` stack contract.

The QEMU test uses the same unchanged assembly ELF on host Linux and in the
private guest root. The guest checks its CS privilege level, zero BSS,
unsupported-call and invalid-pointer errno, byte-exact write and raw exit 5.
The kernel checks the syscall's active root, code/stack permissions, original
root mappings and restored CR3. Malformed headers are rejected, repeat load
and run are rejected, and complete native/reference kernel images match.
Full CI requires this gate rather than counting a missing-tool skip.

Limits remain material:
- This is not the usual low Linux layout at 4 MiB. Moving there would collide
  with kernel identity mappings and needs a separate kernel layout design.
- The boot root must be slot-0-only and the physical pool below 256 MiB, as
  `kspace` requires. No arbitrary live process root can be cloned.
- Trusted resident boot-module pointers only. Not a hostile-pointer API or
  security sandbox. No execute-disable policy or recoverable guest faults.
- No argv, environment, complete auxv, libc, dynamic loader, filesystem,
  memory/process syscalls, threads, signals, networking or GUI support.
- Kernel mappings remain shared supervisor mappings. Interrupt runtime is
  unchanged; the existing return stub briefly enables IRQs before the caller
  restores the boot root. This is not a concurrent scheduler design.
- Tables and frames are not reclaimed; partial allocation failure can leak.
  One-shot lifecycle only, not production exec/exit management.
- Emulator results prove no HP, GPU, ARM64 kernel or POCO hardware support.
