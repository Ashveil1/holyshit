# Owned ELF lifecycle checkpoint

`kownedelf.holy` runs one bounded static ELF program inside an owned address
space (`kowned.holy`) through a full repeatable lifecycle:
prepare -> run -> exit -> reclaim. Existing `kuser`, `klinux`, `klowelf` and
`kspace` loaders and their APIs are unchanged. This is a separate experiment,
not a generic Linux or sandbox claim.

The loader keeps a fixed metadata block allocated once: state, the active
generation handle, entry point, run results, eight load descriptors and nine
readable spans. No per-cycle work allocates lists, strings or tables, so the
bump-heap marker stays stable across cycles and frame reclamation is
measurable against the physical pool baseline.

Validation keeps the `klowelf` static ELF64/x86-64 rules and errno behavior
(write to fd 1/2 on the serial line, -EBADF, -EFAULT, -ENOSYS, exit and
exit_group), constrained to the owned 2 MiB window with the top gap page and
stack page reserved. Overlap checking compares segment ranges in fixed
scratch instead of a dynamic list; the older `klowelf` validator builds a
fresh list per call, which is why it could not prove a repeated-loader leak.

State moves EMPTY -> PREPARING -> READY -> RUNNING -> EMPTY. Validation
finishes before any space exists. A space is published as READY only after
every segment and the stack are mapped, copied and protected. Every
preparation failure destroys the inactive handle and clears the state.
`run` restores the boot root and the normal syscall handler before
destroying the handle. `discard` tears down a prepared program that never
ran. Stale, repeated or out-of-state operations are rejected.

Verified on QEMU with the same static ELF on the host: 100
load/run/exit/cleanup cycles recover the physical frame baseline every
cycle, exit code and syscall counts match the host run, BSS reads zero on
every cycle, segment permissions are published (read-only text/headers,
read-write data and stack, supervisor-only gap), allocation budgets 0..8
fail cleanly at every create/split/segment/stack boundary with the baseline
restored, malformed images are rejected, discard/stale/double-teardown are
rejected, and the native image is byte-identical to the reference image.

Earlier boundary, now fixed: the ring-3 entry stub used to re-enable IRQs
on its return path (`lab_uret` `sti` in `x64gen.py`) before the loader
regained control, so a few instructions ran with IRQs on while the owned
root was still active. The stub now returns with IF clear and every
`enter_user` caller manages interrupts explicitly: the loaders mask IRQs
before touching roots and re-enable them only after restoring the boot
root, and the direct `kuser`/`klinux` runners re-enable them after the
user session has stopped. No IRQ can fire between the user stopping and
the boot root being restored.

Not proven: ELF lifetimes beyond one program at a time, concurrent programs,
fault recovery, NX enforcement, sandboxing, hardware, or general heap
cleanup. Two slots exist in `kowned`; this loader deliberately uses one.
