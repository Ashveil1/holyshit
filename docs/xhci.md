# Experimental USB HID input over xHCI

`kernel/kxhci.holy` adds an opt-in USB input path beside the existing PS/2
keyboard and mouse. It is not imported by any desktop, shell or input-queue
entry point. Default BIOS/UEFI desktop behavior and PS/2 input are unchanged.
This is tested on QEMU, not on an HP or any physical USB hardware.

## Scope

A caller first runs `kpci.init()`, then calls `kxhci.init(pci_index, port,
kind)` with an explicit PCI function, root port and device kind (1 keyboard,
2 mouse). There is no port scan or automatic device selection. One device is
enumerated per boot; initialization is one attempt. All work is polled: no
xHCI interrupts, MSI or event-ring IRQ delivery are used anywhere.

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

This does not implement USB hubs or tiered topology, more than one device,
USB storage or any non-HID class, EHCI/UHCI companion controllers, SuperSpeed
root ports, interrupt-driven completion, endpoint halting/recovery, device
removal, port power management, streams, or any desktop/ring-3 input-queue
integration. Reading keys through the desktop still uses the PS/2 path;
routing USB reports into windows is future work and needs no new syscall for
this module itself (it is kernel-internal like `kahci`).

Polls and command waits have both a 100-PIT-tick limit and a finite iteration
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
per boot. `ready()` reports whether polling is usable; `error()` returns the
current initialization/terminal-failure status.

`poll()` returns 0 when no report completed, otherwise the device kind. Each
completion is copied to a snapshot buffer before the next transfer is armed,
so the report stays stable while polled. `report_bytes()` is the snapshot
length and `report_byte(index)` returns one byte (`-1` outside). Boot
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

Run from the repository root. QEMU provides the controller and devices; no
hardware access, root privileges or host USB involvement is needed.
