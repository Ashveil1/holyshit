# Experimental window input syscalls

The compositor router binds one scene for the single active ring-3 program.
This is a BIOS/QEMU experiment, not a process-isolated desktop or a scheduler.

| Number | Name | Arguments | Result |
| --- | --- | --- | --- |
| 92 | SYS_WIN_EVENT_READ | window id | packed pointer event, or 0 |
| 93 | SYS_WIN_CREATE | x, y, width, height, color | window id, -22 for nonpositive size, -1 without a bound router |
| 94 | SYS_WIN_CLOSE | window id | 0 on removal, -22 if missing |
| 95 | SYS_WIN_KEY_READ | window id | keyboard code, or 0 |

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
