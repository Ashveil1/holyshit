# Experimental USB HID input over xHCI

`kernel/kxhci.holy` adds an opt-in USB input path beside the existing PS/2
keyboard and mouse. It is not imported by any desktop, shell or input-queue
entry point. Default BIOS/UEFI desktop behavior and PS/2 input are unchanged.
This is tested on QEMU, not on an HP or any physical USB hardware.

## Scope

A caller first runs `kpci.init()`, then calls `kxhci.init(pci_index, port,
kind)` with an explicit PCI function, root port and device kind (1 keyboard,
2 mouse). There is no port scan or automatic device selection. At most two
devices are brought up per boot, one keyboard and one mouse on their own
root ports, each with a separate `init` call; initialization is one attempt
per device. All work is polled: no xHCI interrupts, MSI or event-ring IRQ
delivery are used anywhere.

Supported here:

- PCI class/subclass/prog-if `0C/03/30`, exactly the QEMU `qemu-xhci`
  controller (vendor `1b36`, device `000d`); NEC and all other controllers
  are refused;
- a 64-bit memory BAR anywhere in the firmware-assigned physical map (both
  the SeaBIOS below-4GiB and the OVMF above-4GiB assignments are covered);
  xHCI versions 1.0 through 1.2, 4K page size, no
  scratchpad buffers and no USB legacy-support extended capability (a
  legacy-support capability is refused, never taken over);
- exactly the QEMU boot-protocol HID devices (vendor `0627`): the QEMU USB
  Keyboard on one root port or the QEMU USB Mouse, high-speed only, with an
  8-byte keyboard or small mouse boot report on a single interrupt-IN
  endpoint;
- controller stop/reset with bounded waits, one enabled slot, device
  addressing, descriptor parsing (device and configuration), SET_CONFIGURATION,
  boot protocol and idle-rate requests, one configured interrupt endpoint,
  and a single outstanding interrupt transfer that is re-armed after every
  report. Full-speed and low-speed devices are refused before any reset.

This does not implement USB hubs or tiered topology, more than the one
keyboard plus one mouse pair, USB storage or any non-HID class, EHCI/UHCI
companion controllers, SuperSpeed root ports, interrupt-driven completion,
endpoint halting/recovery, device removal, port power management, or
streams.

Desktop integration exists as a separate opt-in layer. `kernel/kusbin.holy`
translates the boot reports into the PS/2-spelling events the window router
already speaks (keyboard usages edge-detected into `readkey_event` codes;
mouse buttons and deltas into packed pointer words, in report order, so a
click edge always lands at the final cursor position). `kwinroute` grows
three hooks - `usb_pointer_fn`, `usb_key_fn` and `usb_only` - drained by
`pump` after the PS/2 FIFOs; with `usb_only` set the PS/2 FIFOs are
drop-drained, so routed input provably arrived over xHCI. The
`kernel/kguiusb.holy` entry runs the normal desktop session on USB input.
Nothing changes for the default entries: with no hooks installed the router
behaves exactly as before, and no new syscall is added (the bridge is
kernel-internal like `kahci`).

Completed interrupt reports are queued per device (depth 32, drop-newest)
between the event-ring drain and the caller's poll, so a host-side pause
that lets completions burst cannot poison the controller. Polls and command
waits have both a 100-PIT-tick limit and a finite iteration
budget. These are conservative prototype limits, not a real-hardware timing
or recovery claim. Any command error, transfer error, descriptor rejection or
timeout stops the controller, disables PCI bus mastering, invalidates the
exposed report, and makes this instance terminal for the rest of the boot.
The whole pinned DMA arena (device context array, command/event/transfer
rings and buffers) is never recycled, including after failure. There is no
retry or reinitialization path.

## API

`init(index, port, kind)` returns true only after the device is addressed,
configured and the first interrupt transfer is armed. One attempt is allowed
per device. `ready()` reports whether polling is usable; `error()` returns
the current initialization/terminal-failure status.

`poll()` returns 0 when no report completed, otherwise the device kind; the
second device uses `poll1()`. Each completion is copied to a snapshot buffer
before the next transfer is armed, so the report stays stable while polled.
`report_bytes()` is the snapshot length and `report_byte(index)` returns one
byte (`-1` outside); `report1_bytes()`/`report1_byte(index)` mirror that for
the second device. Boot
keyboard reports are 8 bytes (modifiers, reserved, six usage IDs); mouse
reports are buttons plus signed deltas. `issued()` counts command-ring
commands and `events()` counts completed interrupt transfers; both back the
refusal/failure gates. The other helpers and globals are kernel
implementation details, not a ring-3 interface. No new syscall is added.

## Reproduce

Only QEMU's emulated controller and devices are used; no host USB device is
ever passed through. `tests/test_xhci.py` boots real q35 kernels built by
both backends, plus the actual OVMF/GRUB UEFI boot path with firmware-owned
controller takeover, checks native-compiler full-ELF identity, injects real keys
(`sendkey`) and pointer deltas (`mouse_move`/`mouse_button`) over QMP into
`usb-kbd`/`usb-mouse`, asserts the decoded boot reports in-guest, cross-checks
the PCI topology with the QEMU monitor, runs nine init-refusal configurations
(wrong class, NEC controller, empty/unimplemented ports, full-speed device,
wrong device kind, and more), and exercises the terminal path with a real
USB stall (requesting descriptor type 9, which the device rejects). DMA guard
regions around every ring and buffer are verified untouched after all of it.

    HS_REQUIRE_XHCI=1 python3 tests/test_xhci.py

`tests/test_usb_desktop.py` boots the `kguiusb` desktop entry with PS/2
drop-drained, injects keys and pointer over QMP, and proves in screendump
pixels that USB input routes into windows: typed characters land in a note
(exactly one edit per injected key) and a window drag lands once. Both
backends and both firmware paths run; the IR leg packages through the real
`build-gui-iso.sh desktop-usb` mode and checks the packaged kernel against
the reference build.

    HS_REQUIRE_GUI=1 HS_REQUIRE_XHCI=1 HS_REQUIRE_UEFI=1 python3 tests/test_usb_desktop.py

Run from the repository root. QEMU provides the controller and devices; no
hardware access, root privileges or host USB involvement is needed.
