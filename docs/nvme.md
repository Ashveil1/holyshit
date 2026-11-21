# Experimental read-only NVMe

`kernel/knvme.holy` adds an opt-in NVMe namespace read path beside the
existing legacy ATA PIO driver and the opt-in AHCI path. It is not imported
by any desktop, shell or volume entry point. Default BIOS/UEFI desktop
behavior and ATA-backed note saves are unchanged. This is tested on QEMU,
not on an HP or any physical disk.

## Scope

A caller first runs `kpci.init()`, then calls `knvme.init(pci_index)` with an
explicit PCI function. There is no controller scan beyond class selection, no
namespace beyond 1, and no mount. Initialization takes ownership of the
selected controller: it disables it before touching queue registers, and
there must be no other driver using it.

Supported here:

- PCI class/subclass/prog-if `01/08/02` (NVM Express, NVM command set);
- a 64-bit memory BAR0, mapped where firmware put it, both below 4GiB
  (SeaBIOS) and above 4GiB (OVMF);
- controllers reporting contiguous queues, a doorbell stride of at most
  16 bytes, the NVM command set, 4KiB minimum host page size, and an NVMe
  1.x version register;
- namespace 1 with 512-byte logical blocks (other block sizes are refused);
- one admin queue pair and one IO queue pair, 8 entries each, in a pinned
  low physical DMA arena; completions are polled by phase tag, never by
  interrupt. Data commands use PRP only. IDENTIFY (controller and namespace)
  and READ, 1..8 sectors per read. No storage-write opcode is accepted, even
  by the internal command helper.

This does not implement writes, flushes, or any other command; multiple or
larger queue pairs; MSI, MSI-X or interrupt-driven completions; SGLs;
namespaces beyond 1; shutdown notification; hotplug, removal or recovery;
partitions or filesystems. A command error, unexpected completion or timeout
hides the result and makes this instance terminal for the rest of the boot.
The whole DMA arena remains pinned and is never recycled, including after
failure. There is no retry or reinitialization path.

Polls have both a 100-PIT-tick limit and a finite iteration budget. These are
conservative prototype limits, not a real-hardware timing or recovery claim.

## API

`init(index)` returns true only after validated IDENTIFY transfers and one
created IO queue pair. One attempt is allowed per boot. `ready()` reports
whether reads are usable; `error()` returns the current
initialization/terminal-failure status.

`read(lba, count)` returns a Boolean and checks capacity without addition
wraparound; LBAs at or above 2^48 are refused outright. It never accepts a
destination address: the sole DMA destination is the driver's own 4096-byte
payload buffer. A successful read replaces that buffer. `byte_at(index)`
returns a byte in the most recent valid transfer or `-1` outside it. A
refused or failed read invalidates all previously exposed bytes.
`sectors()` returns the namespace capacity while ready, otherwise 0.
`commands()` is an issued-command counter used by the refusal/failure gates.
`issue(opcode, lba, count)` is the low-level helper the refusal battery
drives; it refuses every opcode except READ before any MMIO. The other
helpers and globals are kernel implementation details, not a ring-3
interface. No new syscall is added.

## Reproduce

Only use host-created disposable images. Never pass a host block device,
physical drive, user disk, or an image containing anything important.

```sh
HS_REQUIRE_NVME=1 HS_REQUIRE_UEFI=1 python3 tests/test_nvme.py
```

The required full-CI step installs QEMU, OVMF, EFI GRUB and FAT/ISO tools.
`HS_TEST_QEMU`, `HS_GRUB_EFI_DIR`, `HS_OVMF_CODE` and `HS_OVMF_VARS` can
point to alternate local installations. A configured missing dependency
fails; unconfigured UEFI tools are optional unless `HS_REQUIRE_UEFI=1` is
set. `HS_REQUIRE_NVME=1` makes missing QEMU fail instead of skipping.
`HS_NVME_EVIDENCE` retains serial, stderr and monitor PCI evidence plus disk
verification records. Quick suites skip this hardware-emulation test; full
suites register it and CI also runs it as a required named step.

The 18-boot gate checks both IR and retained AST kernel backends:

- complete native/reference kernel ELF identity and boot of those native
  bytes, plus actual OVMF/GRUB UEFI boots using read-only firmware code and
  disposable variable-store copies;
- QEMU q35 guest BDF/vendor/device against the monitor's own PCI table;
- dense 32MiB namespace reads, 1..8-sector spans, final sectors, DMA
  alignment, guard bytes and controller-ready state;
- a sparse 2TiB+32MiB virtual namespace, with reads crossing both LBA28 and
  LBA32. Every sector carries its full six-byte LBA, so truncated high
  address bits cannot pass with a repeating low-byte pattern;
- missing/wrong controller, invalid index and 4Kn sector-size refusal;
  invalid spans/opcodes issue no command;
- actual QEMU blkdebug EIO and throttled-I/O timeout, terminal refusal after
  failure, and retained DMA guard bytes;
- unchanged complete allocated disk bytes, hole boundaries, size, allocation
  count and mtime after all boots, not merely unchanged sampled sectors.
  Sparse-image setup is fsynced before the baseline audit.

The sparse file needs support for files larger than 2TiB and `SEEK_DATA` /
`SEEK_HOLE`; it consumes only a small number of data extents, not 2TiB of
host storage. The dense fixture consumes 32MiB.

## Remaining HP gate

An OVMF/q35 pass is not evidence of HP controller, firmware, keyboard, mouse,
display or boot-media compatibility. The GUI still uses PS/2 input and its
existing framebuffer path. This NVMe path is not connected to note storage,
and no physical-hardware trial is authorized by this milestone.

Register and command reference:
[NVM Express 1.4b specification](https://nvmexpress.org/wp-content/uploads/NVM-Express-1_4b-2020.09.21-Ratified.pdf),
sections 3.1, 3.3, 4.1, 4.6 and 7. The proof above is limited to the
exercised QEMU model and the explicit restrictions in this document.
