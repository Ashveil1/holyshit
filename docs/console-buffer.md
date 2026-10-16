# Fixed console byte storage

`kernel/kconsole_buffer.holy` is a separate storage primitive for the OS lane,
not yet wired into the graphical console. It replaces neither the runtime
allocator nor `std.console`. Trusted callers create one opaque state with
capacity1..256 ASCII bytes and retained1..16 lines. One raw allocation stores
the active line and a ring of history slots. A fixed length array and scalar
state hold lengths, next slot, history count and submission count.

`feed(state,byte)` accepts an integer0..255 or null. Newline10 submits even an
empty line, evicts the oldest if full, resets the active length and returns
true. Backspace8 removes one active byte; printable32..126 appends until full.
Other bytes/null do nothing. Invalid types/ranges fail before changing state.
`reset` clears only the active length. `history_address` and `history_length`
address retained lines oldest first with a checked index. The caller may read
exactly the active length at the base or a retained length at its address.
Unused/stale bytes are not cleared and are not part of the text. Do not read
past length, mutate state fields or free the backing allocation separately.
This is trusted unsafe kernel memory, not a boundary for hostile state.

The valid edit/submission path creates no new source strings, Lists, slices,
ranges or raw allocations after creation. It copies at most capacity bytes on
submission and uses a fixed circular history. Error reporting, snapshots,
keyboard readkey strings, rendering and logging remain outside that statement.
Integer counter overflow is not handled; no infinite-lifetime promise.
This primitive reduces one specific lifetime source. The existing graphical
console still uses allocating strings/history and its16MiB bump heap still
has no general reclamation. No GC, allocator replacement, daily terminal or
performance claim is made. Raw data lives for the lifetime of its owner.

`tests/test_console_buffer.py` compares400 independently modeled transitions
and errors on interpreter/GCC/x64/native-seed, plus1/256 capacity and1/16
retention extremes. A separate generated kernel runs100000 submissions and
500000 feed calls with backspace, history addressing and reset in the loop.
Two raw one-byte allocation markers surround the loop: the second address
must be exactly16 bytes after the first, the freestanding allocation alignment,
with no intervening bump allocation. Snapshots/serial output happen afterward.
Native/Python complete image equality is checked; full CI builds the kernel
driver with the audited seed. `--python-bootstrap` changes only that kernel
driver's local diagnostic build. This is finite storage-lifetime evidence,
not a framebuffer, interactive keyboard, throughput or general heap proof.
