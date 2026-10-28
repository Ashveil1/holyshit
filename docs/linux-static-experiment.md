# Experimental static Linux write/exit personality

This is a small emulator experiment on the native Holyshit kernel, not a
Linux kernel replacement and not general Linux application compatibility.
`klinux.holy` is separate from the existing Holyshit `kuser` loader and
`ksyscall` dispatch. Those files and their ABI are unchanged.

The test links one x86-64 static ET_EXEC assembly program at a deliberately
high virtual address inside the existing reserved user region. The same
unchanged ELF runs on host Linux and in ring 3 on our kernel. It writes the
exact nine bytes `linux-ok!` without an extra newline, checks syscall return
values, checks zero BSS, and exits with raw status 5. The test requires full
native/reference kernel image equality. This proves only this bounded ABI
slice, not ordinary distribution binaries or libc support.

Supported calls: write(1 or 2, buffer, count), exit, exit_group. Unsupported
calls return -ENOSYS. Bad descriptors return -EBADF; out-of-image buffer
ranges and writes larger than 65536 bytes return -EFAULT. Output goes to
COM1. Empty write returns zero for stdout/stderr without dereferencing its
pointer. Exit status is the low eight bits, with no Holyshit tag decoding.
After return to the kernel, the normal Holyshit syscall handler is restored.

Loader restrictions: little-endian ELF64, x86-64, ET_EXEC; at most eight
program headers and 16 MiB of mapped segment pages. PT_LOAD plus ignored
PT_NULL/PT_GNU_STACK only. Segment pages cannot overlap, must be new mappings,
and must lie in [USER_BIAS, USER_BIAS + 128 MiB). The entry must lie in an
executable file-backed segment. Only R, RX and RW segment flag sets are
accepted. No relocation or address bias is applied. File/table bounds are
checked before referenced reads; newly mapped pages are zeroed before copy.
Tests mutate/restore real boot-module headers to check rejection paths.

Important limits:
- No low-address Linux layout, dynamic loader, shared libraries, TLS, argv,
  environment, auxv, libc startup, filesystem, memory syscalls, signals,
  threads, process management, networking or GUI.
- The minimal aligned stack is empty, not a complete Linux process stack.
- This uses the existing shared page tables. It is not a sandbox for hostile
  programs. Execute-disable protection, per-process address spaces and
  resource lifetime are not implemented here.
- Loading is one-shot. Mappings are not reclaimed on exit or partial map
  failure. Header validation happens before allocation, but allocation
  failure can leak pages. Retry/replacement is not a supported lifecycle.
- The kernel caller supplies a valid resident boot-module span. This is not
  an arbitrary-pointer loader API.
- No HP/GTX950M, ARM64 kernel or POCO creek hardware result is implied.

Run `HS_REQUIRE_LINUX_STATIC=1 python3 tests/test_linux_static.py` with GNU
as/ld and QEMU on an x86-64 Linux host. GNU tools build only the Linux fixture;
the kernel still builds through Holyshit's freestanding backend. Full CI
requires the experiment rather than counting a missing-tool skip as proof.
