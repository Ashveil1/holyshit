# Private low mapping experiment

`kspace.holy` is small x86-64 paging groundwork, separate from the current
Linux loader. It clones the boot root's page-table hierarchy into new
kernel-owned tables and replaces one page in a bounded low virtual window
with a fresh zeroed user frame. Splitting an identity-mapped huge page in the
new hierarchy does not change the original root or its neighboring pages.

The actual QEMU test creates two roots, maps the same virtual address to
different physical frames, switches CR3 between them, writes different
values, switches back and verifies both values and the unchanged boot root.
It checks zero initialization, supervisor-only neighbor/kernel leaves,
invalid address/alignment/active-root rejection, and complete native versus
reference kernel image equality. Full CI requires QEMU, not an optional skip.

The same test also maps identical machine-code bytes and separate user stack
pages at the same virtual addresses in both roots. Each actual ring-3 run
checks CS.RPL is 3, reads that root's marker and passes it through an exit
syscall. The handler checks the active CR3, then the test restores the boot
root and verifies the kernel and both frame values remain intact. Code leaves
are user-read-only and stack leaves are user-writable. No new kernel runtime
or loader implementation is introduced by this extension.

This is not yet a Linux loader integration, production user-process switcher
or hostile program sandbox. The earlier data checks execute at ring 0; the
new instruction and syscall checks execute in ring 3. Existing Holyshit and Linux
personality loaders remain unchanged. No low-address Linux program support
is claimed from this test.

Bounds and lifecycle:
- Trusted kernel-internal roots only. `map_user` requires a root created by
  this module; it is not an arbitrary physical-pointer API.
- Initial root must have only PML4 slot 0 in use. This is a boot-only fixture,
  not cloning a live user process or supporting concurrent root edits.
- Virtual user window is 256-512 MiB, deliberately outside the small guest's
  physical frame pool. Creation rejects a physical pool extending above
  256 MiB to avoid replacing the identity alias of kernel-owned frames.
- Kernel identity leaf mappings remain supervisor-only. No execute-disable
  policy, ASLR, resource limits, guard fault recovery or independent kernel
  address-space separation has been added.
- Page tables use the existing bump heap. Frames and tables are not reclaimed;
  repeated creation or a failed partial allocation is not a supported
  production lifecycle. Existing limitations must be addressed before a
  process/sandbox claim.
- No PC, GPU, ARM64 kernel or POCO hardware verification is implied.
