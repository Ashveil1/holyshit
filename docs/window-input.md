# Experimental window input syscalls

The compositor router binds one scene for the single active ring-3 program.
This is a BIOS/QEMU experiment, not a process-isolated desktop or a scheduler.

| Number | Name | Arguments | Result |
| --- | --- | --- | --- |
| 92 | SYS_WIN_EVENT_READ | window id | packed pointer event, or 0 |
| 93 | SYS_WIN_CREATE | x, y, width, height, color | window id, -22 for nonpositive size, -1 without a bound router |
| 94 | SYS_WIN_CLOSE | window id | 0 on removal, -22 if missing |
| 95 | SYS_WIN_KEY_READ | window id | keyboard code, or 0 |
| 96 | SYS_WIN_FILL | window id, x, y, width, height, RGB24 | 0, -22 for invalid arguments, -12 for unavailable body storage |
| 97 | SYS_WIN_PRESENT | none | full scene pixel count, -19 without a bound target |

Exit closes windows created through SYS_WIN_CREATE and drops their input queues.
Window ids are scene-local, not permission tokens. There is no multi-process
ownership enforcement in this interface yet.

## Keyboard policy

A left press on a window focuses it. Hover does not change focus. A desktop
press or removal of the focused window clears focus. Keyboard input goes only
to the live focused window; no-focus input is dropped. Queued keys stay with
the window that had focus when the router accepted them, even after a later
focus change. Closing the window drops that queue.

SYS_WIN_KEY_READ returns the oldest accepted key for the requested window,
not necessarily the window currently focused. It returns 0 for a missing
window, no bound router, or a wait that expires with no key. Codes follow
[the ordered keyboard stream](keyboard-events.md): ASCII byte codes and
Up=128 / Down=129. They are translated make events, not raw scancodes or
key-up events. Each window queue holds 64 keys and drops newest on overflow.
Pointer events use separate queues and keep their existing packed format.

Both read syscalls open a ring-0 interrupt window and pump both hardware
FIFOs while waiting, for at most 400 timer ticks per call. This is a bounded
busy wait, not a sleeping task or a guarantee about wall-clock latency.
Pointer batches run before keyboard batches so pending clicks update focus
before pending keys. The hardware FIFOs have no shared timestamp; this does
not guarantee total ordering between simultaneous mouse and keyboard input.
The unified keyboard stream is consumed by the router while either window
read is waiting, so another consumer must not also drain that stream.

`tests/test_winkeys.py` checks focus, hover, no-focus, stale-focus, overflow,
queue isolation and cleanup in ring 0, then uses QMP clicks and keys while a
ring-3 app waits on its two app-created windows. It checks the exact sequence
window 1: a / Up / Enter, window 2: b / Down, on IR and AST kernels.
It does not claim hardware, Unicode, shift, USB, or multi-process validation.

## Persistent app-drawn bodies

SYS_WIN_FILL paints an opaque RGB24 rectangle in the window's body, with
(0,0) immediately below the title bar. Rectangles clip to the body, so an
app cannot paint over title chrome or another window. Colors must be
0..16777215 and coordinates/dimensions must be within -1048576..1048576.
An unknown window or an out-of-range argument returns -22. Nonpositive or
fully clipped rectangles are successful no-ops with no allocation.

The first visible fill lazily allocates a body buffer and initializes it to
the window's original background color. Buffers are limited to 4096 pixels
per dimension and 4194304 pixels total; an oversized body or failed heap
allocation returns -12. Moving or raising a window preserves its body;
removal or app exit frees the body buffer. Creation without drawing remains
lazy and uses the original solid-color body path.

Drawing changes stored content, not the hardware framebuffer directly.
The app can request composition and flush through SYS_WIN_PRESENT after
the kernel binds a framebuffer target.
This interface does not add a display server, automatic repaint loop,
user-mapped pixel buffers, text rendering, alpha blending or resizing.
Direct callers of kcomp.compose still own scene-background clearing; the
presentation path described below clears it automatically.

`tests/test_winpaint.py` tests body clipping, title protection, retained
content on raise/move, errors, failed allocation and heap reclamation.
A ring-3 app creates two overlapping windows and sends four fill syscalls.
A test-only exit observer captures the live scene before normal exit
cleanup, composing and flushing to a mock RGB32 framebuffer. Python checks
every one of its 3072 RGB pixels against a separate raster oracle, on IR
and AST kernels. This is not a physical-display or real-hardware test.

## Explicit scene presentation

The kernel calls `kwinroute.bind_frame(router, descriptor, background)`
with its own mapped framebuffer descriptor and desktop RGB24 color.
The descriptor must match the scene dimensions, use 3 or 4 bytes per pixel,
have enough row pitch, and have three distinct channel offsets inside a
pixel. Invalid binds return false without changing an existing binding.
The kernel is responsible for the descriptor's mapped, writable memory
and lifetime; structural checks are not address-space validation.

Ring 3 supplies no framebuffer pointer. SYS_WIN_PRESENT processes pending
pointer and key input, clears the whole back buffer to the desktop color,
composes all windows and the cursor, then flushes the complete scene to the
bound target. It returns width times height, or -19 if no router or target
is bound. Every present is a full repaint, not incremental damage tracking.
This clears stale window/cursor pixels after movement and removal. Closing
a window also presents the remaining scene when a target is bound, including
close calls made by normal app-exit cleanup. Without a target, old headless
routing/drawing behavior is unchanged.

This is still cooperative: drawing and queued input do not repaint until
present or close runs. There is no background display task, resize event,
frame timing guarantee or physical-display validation in this milestone.
`tests/test_winpresent.py` uses a kernel-bound mock framebuffer. It checks
padded RGB24 rows and guards, descriptor failures, movement/cursor clearing,
and preservation of unused RGB32 bytes. A ring-3 app paints two windows,
presents, closes the top window, and exits. All 9216 RGB pixels across those
three target states are compared to a separate Python oracle on IR and AST.
The test observer only reads target memory; it does not compose or flush.
