# Multi-submission display-only console experiment

`kernel/kconsole_session.holy` is a separate framebuffer demo that keeps
accepting input after Enter. The original single-line console is unchanged.
Input is displayed, never evaluated as a command, agent request or code.

`std.console.create(capacity, retained)` wraps the existing ASCII line editor:
capacity1..256, retained1..16, state `[line_state, recent_lines, retained,
submission_count]`. `feed(state,key)` returns true on submission, appends the
line (including empty lines), keeps only the newest retained lines, increments
the count, then resets the active line. Other keys return false with the
existing line editor validation and behavior. Treat state fields as opaque;
mutation or alias preservation of replaced history lists is not supported.

The demo keeps four submitted lines of42 ASCII characters and a fresh input
line. Lowercase displays uppercase through the existing bitmap font. It
redraws text rows rather than the entire panel per key. It has no cursor,
scrollback navigation, up-arrow recall, command dispatch, filesystem action,
model, networking, Unicode or terminal emulation. Keyboard input retains the
63-byte software FIFO's capacity and drop-newest limits.

Important lifetime limit: the freestanding runtime still uses its existing
16MiB bump allocator without reclamation. Bounded retained text does not mean
bounded total allocations over time. Editing/rendering allocates; a long
session can run out of memory and halt. This demo proves six submissions,
old-line eviction and a seventh editable line, not an indefinitely usable
terminal. Raising heap limits would hide that missing lifetime work, not fix
it, so this change does not change the allocator.

`tests/test_console_state.py` compares200 independently modeled transitions
and invalid limits on interpreter, GCC, x64 and native-seed compiled paths.
`tests/test_console_session.py` checks complete native/Python kernel image
identity, boots GRUB/QEMU, enters six lines (including backspace), verifies
four retained lines and checks actual C/D/E/F/G text pixels. GRUB/xorriso are
optional dependencies; this visual boot gate skips without them. The pure
state gate still runs. No real-hardware/UEFI claim is made.

The demo now uses [direct framebuffer text](kernel-font.md) rather than
software surfaces/full pixel-list copies. The six-submission visual layout
is unchanged. This reduces a source of rendering allocations, but does not
remove the bump-heap lifetime limit described above.
