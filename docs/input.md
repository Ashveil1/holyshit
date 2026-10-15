# Early keyboard line editing

`std.lineedit` keeps a bounded ASCII line independent of keyboard hardware.
`create(capacity)` returns an empty state; capacity is an integer1..256.
`feed(state,key)` accepts null (no event) or a single character. Printable
ASCII appends until capacity, backspace deletes, and newline submits the line.
Other single-character input is ignored. `reset(state)` clears it.

State layout is `[text,submitted,capacity]`. Read the fields, but do not write
fields or fabricate states. A submitted state ignores further events until
reset. Invalid key types/lengths raise before changing the line. The module
creates one backspace byte with portable memory builtins because the language
has no backspace escape. It does not read or write hardware itself.

```
import std.lineedit
line = std.lineedit.create(64)
std.lineedit.feed(line, "a")
std.lineedit.feed(line, "\n")
print line[0], line[1]
```

A freestanding caller may feed `readkey()` events; the existing x86 keyboard
backend is lowercase ASCII with one event slot. This helper adds no input
queue, shift handling, mouse, Unicode composition or full terminal editing.
The QEMU test waits for a guest-ready marker, injects a/b/backspace/c/enter,
and requires the resulting line `ac` from the guest. That tests keyboard
routing and edits, not an interactive desktop or an AI agent.

The OS direction is agent-centered: a future natural-language agent should
mediate apps, files and system operations through bounded APIs. Text entry
is preparation only. No model runtime, agent privilege policy or general
agent control is implemented by this module.
