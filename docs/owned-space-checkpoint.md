# Owned-space allocation and reclamation checkpoint

`kowned.holy` is separate from the existing page-table and ELF experiments.
It owns its root, cloned intermediate tables, split table and user frames
through explicit ledgers. Supervisor identity leaf frames are borrowed and
never freed. Existing `kpage`, `kspace`, `kpmm` and loaders are unchanged.

The fixed metadata block is allocated once. It has two reusable slots,
generation-tagged handles, sixteen table entries and 512 user-frame entries
per slot. All owned physical pages come from the existing bitmap pool and
are zeroed. The repeated path avoids growing lists or allocating page tables
from the bump heap. The private free helper checks page alignment, pool bounds
and allocated bitmap state, and is used only on ledger-recorded frames.
It uses integer frame-index math: the existing general `kpmm.free` uses `/`,
which creates Float objects on this compiled path and moved the bump marker
by 9600 bytes over 100 cycles in the initial local test. No general allocator
semantics were changed to fix that unrelated shared path.

Creation accepts a boot-like slot-0-only supervisor hierarchy and a physical
pool below 256 MiB. The user mapping window is one 2 MiB identity region at
256 MiB. Mapping splits that region privately; no generic arbitrary-table
mutation API is offered. All necessary pages are allocated before entries
change, so a failed map restores the allocation baseline and leaves prior
mappings intact. Clone failure unwinds its recorded tables before publishing
a handle. A deterministic allocation budget exercises each failure boundary.

Destroy accepts only a known, inactive generation handle. It releases user
frames and tables from their own ledgers, clears the slot, and rejects stale,
unknown, repeated or active-root destruction. It never derives ownership
from a walk over identity-mapped leaf entries. No reclaim of older bump-heap
page tables is attempted.

Actual QEMU tests check 100 create/map/switch/destroy cycles, bitmap free-frame
baseline after each cycle, a stable 16-byte bump-allocation marker gap after
metadata warmup, allocation-budget clone/map failure unwind, unchanged prior
mappings, two-slot exhaustion/reuse, stale handles, active-root refusal,
borrowed kernel data and boot table preservation. Complete native/reference
kernel images must match. Full CI requires QEMU rather than accepting a skip.

This first checkpoint is not integrated with ELF execution. It does not yet
prove repeated load/run/exit cleanup, scheduling, fault recovery, NX policy,
hostile-process isolation, arbitrary root support, general heap repair or any
PC/ARM64/phone hardware support. A separate approved integration step is
needed before a repeatable program-lifecycle claim. Callers are trusted
kernel code; ledgers and metadata are not hostile-pointer APIs. Generation
reuse stops after one million creations per slot rather than wrapping.
