# Separate bounded command-console experiment

`kernel/kcommand_console.holy` is an x86-64 graphical kernel demo with an
actual small command path. The existing `kconsole_fixed.holy` remains
unchanged and display-only. Neither is a general shell or desktop.

The shared `kcommand.execute(result, address, length)` API accepts a trusted
caller-owned span of up to256 printable ASCII bytes. It trims outer spaces,
recognizes lowercase `help` with no arguments and `echo` with a literal text
argument, and produces bounded output in a separately owned result buffer.
Commands are case-sensitive even though the bitmap font draws uppercase.
There is no parsing of semicolons, substitution, paths or programs. Unknown
commands produce `UNKNOWN COMMAND`; empty input clears the result. `echo`
truncates to the configured capacity and reports a distinct status.

The result record owns its raw byte storage: `[address, capacity, length,
status]`. Capacity is16..256. Status is0 empty,1 help,2 echo,3 unknown,4
truncated echo. Input validation completes before replacing the previous
result. This is a trusted kernel-internal API, not a hostile pointer boundary;
callers must supply valid memory and must not overlap input/output storage.
The typed console uses its separate42-byte edit buffer, retains four input
lines and displays one result row. It preserves existing edit/Up/Down history
helpers but does not change their display-only demo.

`tests/test_kcommand.py` boots the shared API in an actual QEMU kernel,
covering spacing, command boundaries, case, literal semicolons, exact/full and
truncated output, invalid input and fixed-buffer integration. It requires
complete kernel image equality from the Python reference and audited native
hs compiler. `tests/test_command_console.py` boots the actual separate demo
through GRUB, injects real PS/2 keys and compares every output-row pixel with
independent glyph masks after help, echo, unknown and empty input. Full CI
requires this graphical gate rather than accepting an optional-tool skip.

Local640x480 guest screenshots were visually inspected for readable layout,
correct help/echo/unknown results and cleared output. These are emulator
checks, not HP laptop, GTX950M, ARM64 kernel or POCO creek hardware proof.
There are no processes, filesystem commands, networking, model integration
or AI authority here. The AI-centered OS goal remains separate future work.
