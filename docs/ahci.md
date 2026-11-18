# Experimental read-only AHCI

`kernel/kahci.holy` adds an opt-in SATA path beside the existing legacy ATA
PIO driver. It is not imported by any desktop, shell or volume entry point.
Default BIOS/UEFI desktop behavior and ATA-backed note saves are unchanged.
This is tested on QEMU, not on an HP or any physical disk.

## Scope

A caller first runs `kpci.init()`, then calls `kahci.init(pci_index, port)`
with an explicit PCI function and port. There is no automatic disk selection
or mount. Initialization takes ownership of the entire selected HBA, not just
the selected port: it refuses outstanding work, stops all implemented ports'
command and receive engines, and disables their interrupts. There must be no
other driver using that HBA. All other ports remain stopped.

Supported here:

- PCI class/subclass/prog-if `01/06/01`, AHCI versions 1.0 through 1.3.1;
- a 32-bit, non-prefetchable BAR5 in the upper 1..4GiB physical range;
- a firmware-initialized, active, direct SATA disk with LBA48 and 512-byte
  logical sectors, on an explicitly implemented port 0..31;
- IDENTIFY DEVICE and READ DMA EXT, slot0, one PRDT entry, 1..8 sectors per
  read. No storage-write opcode is accepted, even by the internal command
  helper. DMA uses a pinned low physical arena, not a virtual-heap pointer.

This does not implement AHCI mode switching, controller/port resets,
firmware-ownership handoff waits, hotplug, spin-up, sleeping links, NCQ,
interrupt-driven completions, ATAPI, port multipliers, 64-bit BARs, writes,
flushes, partitions or filesystems. Firmware ownership/busy state is refused,
not forcibly taken over. Native 4Kn disks are refused by the IDENTIFY decoder;
that refusal has not been exercised with a real/emulated 4Kn device.
NVMe and USB storage are different drivers and are not covered.

Polls have both a 100-PIT-tick limit and a finite iteration budget. These are
conservative prototype limits, not a real-hardware timing or recovery claim.
A command error, short transfer or timeout disables PCI bus mastering, hides
the result, and makes this instance terminal for the rest of the boot. The
whole DMA arena remains pinned and is never recycled, including after failure.
There is no retry or reinitialization path.

## API

`init(index, port)` returns true only after a validated IDENTIFY transfer.
One attempt is allowed per boot. `ready()` reports whether reads are usable;
`error()` returns the current initialization/terminal-failure status.

`read(lba, count)` returns a Boolean and checks capacity without addition
wraparound. It never accepts a destination address: the sole DMA destination
is the driver's own 4096-byte payload buffer. A successful read replaces that
buffer. `byte_at(index)` returns a byte in the most recent valid transfer or
`-1` outside it. A refused or failed read invalidates all previously exposed
bytes. `sectors()` returns the LBA48 capacity while ready, otherwise 0.
`commands()` is an issued-command counter used by the refusal/failure gates.
The other helpers and globals are kernel implementation details, not a
ring-3 interface. No new syscall is added.

## Reproduce

Only use host-created disposable images. Never pass a host block device,
physical drive, user disk, or an image containing anything important.

```sh
HS_REQUIRE_AHCI=1 HS_REQUIRE_UEFI=1 python3 tests/test_ahci.py
```

The required full-CI step installs QEMU, OVMF, EFI GRUB and FAT/ISO tools.
`HS_TEST_QEMU`, `HS_GRUB_EFI_DIR`, `HS_OVMF_CODE` and `HS_OVMF_VARS` can point
to alternate local installations. A configured missing dependency fails;
unconfigured UEFI tools are optional unless `HS_REQUIRE_UEFI=1` is set.
`HS_REQUIRE_AHCI=1` makes missing QEMU fail instead of skipping.
`HS_AHCI_EVIDENCE` retains serial, stderr and monitor PCI evidence plus disk
verification records. Quick suites skip this hardware-emulation test; full
suites register it and CI also runs it as a required named step.

The 28-boot gate checks both IR and retained AST kernel backends:

- complete native/reference kernel ELF identity and boot of those native
  bytes, plus actual OVMF/GRUB UEFI boots using read-only firmware code and
  disposable variable-store copies;
- QEMU q35/ICH9 guest BDF/vendor/device against the monitor's own PCI table;
- dense 32MiB SATA images on port 0 and port 4, 1..8-sector reads, final sectors,
  DMA alignment, guard bytes, disabled interrupts and stopped other engines;
- a sparse 2TiB+32MiB virtual image, with reads crossing both LBA28 and LBA32.
  Every sector carries its full six-byte LBA, so truncated high address bits
  cannot pass with a repeating low-byte pattern;
- missing/wrong controller, invalid index, negative/out-of-range/unimplemented
  ports, absent media and ATAPI refusal; invalid spans/opcodes issue no command;
- actual QEMU blkdebug EIO and throttled-I/O timeout, terminal refusal after
  failure, disabled bus mastering and retained DMA guard bytes;
- unchanged complete allocated disk bytes, hole boundaries, size, allocation
  count and mtime after all boots, not merely unchanged sampled sectors.
  Sparse-image setup is fsynced before the baseline audit.

The sparse file needs support for files larger than 2TiB and `SEEK_DATA` /
`SEEK_HOLE`; it consumes only a small number of data extents, not 2TiB of host
storage. The dense fixture consumes 32MiB.

## Remaining HP gate

An OVMF/q35 pass is not evidence of HP controller, firmware, keyboard, mouse,
display or boot-media compatibility. The GUI still uses PS/2 input and its
existing framebuffer path. This AHCI path is not connected to note storage,
and no physical-hardware trial is authorized by this milestone.

Register/layout and initialization reference:
[Intel AHCI 1.3.1 specification](https://www.intel.com/content/dam/www/public/us/en/documents/technical-specifications/serial-ata-ahci-spec-rev1-3-1.pdf),
sections 3, 4, 10.1 and 10.3. The proof above is limited to the exercised QEMU
model and the explicit restrictions in this document.
