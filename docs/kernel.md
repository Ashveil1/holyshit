# kernel freestanding (`hs.py xkernel`)

The kernel is written in pure `.holy` - no C/asm in the kernel line. The
x86-64 assembler/linker lives in `x64.py`, the runtime in `x64gen.py`
(serial COM1, bump heap, IDT/PIC/PIT, `ticks`/`readkey`, tagged values)

```sh
python3 hs.py xkernel kernel/xdemo.holy -o k.elf
qemu-system-x86_64 -kernel k.elf -serial stdio -display none
```

Examples in `kernel/`: `xdemo` (boot+fib), `kx2` (timer/keyboard/PMM),
`kxstr`/`kxlist`/`kxslice` (values over serial), `ktry` (try), `kimp` (import),
`kxexc_*` (EXC report), `kprim` (primitives), `kpaging` (paging)
Real modules: `kmb` `kpage` `kpmm` `kheap` `kaddr` `ktask` `kvfs` `kramdisk`
`ksyscall` `kuser` (example user program: `uuser`, shell: `uush`)
QEMU tests: `kpmmtest` `kheaptest` `kaddrtest` `ktasktest` `kpreempt`
`kfstest` `kring3` `kring3ret` `kring3wr` `kusermode` `kiotest` `kushtest`

## What exists on the kernel

- `print` goes to serial, `ticks()` at 100Hz, `readkey()` returns the latest key or Null
- `pmm_alloc(n)` / `pmm_total()` / `pmm_free()` (4K pages starting at 64MB - legacy;
  real code uses `kpmm` below)
- boot info: `mb_info()` (the bootloader's struct), `mb_magic()` (magic from EAX),
  `image_end()` (first address after the kernel image: code + `.data` holding the main
  stack + boot page tables - the PMM reserves up to here; beyond it the bootloader
  might overwrite our things)
- `read_mem(ptr, n)` - read raw memory as a Str (byte by byte); used for the
  bootloader structs and the ramdisk image
- paging: `cr2()`/`cr3()`/`set_cr3(p)`, `invlpg(vaddr)`, `tlb_flush()`
- port I/O: `ioport_in(port, size)` / `ioport_out(port, value, size)`
  (size = 1/2/4 bytes, values are untagged machine words) - the only way the kernel
  touches hardware registers, because `asm` exists only on the native side
- full `unsafe:` (`alloc`/`load`/`store` incl. `load64`/`store64`, struct) -
  this is how you touch hardware
- ATA: `kata` (primary/master/LBA28, PIO) - `present()`, `read_identify()`,
  `sectors()`, `model()`, `read`/`write(lba, count, buf)` (count 1..256);
  the `katatest` test boots with `-drive if=ide`
- `import` works (plain `.holy` modules), `try` works (halt when no handler)

## memory management (pure `.holy`)

- `kernel/kmb.holy` - reads the bootloader memory map, supporting 2 layouts (detected by
  validation, not by trusting EBX): the multiboot1 spec and QEMU's own 88-byte struct
  (layout does not match the spec - see QEMU source `hw/i386/multiboot.c`)
- `kernel/kpage.holy` - 4-level page tables: `map`/`unmap`/`translate`,
  `is_mapped`, `map_phys`/`map_user`, `protect` (change permissions later,
  used to make user text read-only); missing tables are created automatically,
  huge pages (2MB/1GB) are split into 512 children when a 4K map lands inside,
  TLB flushed every time; user mappings carry the U/S bit down the whole path
  (kernel mid-level tables stay supervisor - otherwise ring 3 faults at the first iret)
- `kernel/kpmm.holy` - a real bitmap frame allocator (`std.bitmap`):
  takes frames from the largest usable region, reserves image/boot window/heap/
  its own bitmap; `alloc(n)` returns a 4K-aligned address, `free`/`free_run`
  return to the pool, `busy(paddr)` asks whether a frame is reserved
- `kernel/kheap.holy` - kmalloc (`std.heap` K&R malloc/free) over real frames mapped
  at `0x60000000`: `init(npages)`, `malloc`/`free`, `free_bytes`
- `kernel/kaddr.holy` - one PML4 per address space sharing kernel-side mappings
  (PML4[0]); `new`/`switch`/`current`; user pages must live at `>= 0x8000000000`
  (PML4 slot 1+) to be truly isolated
- `kernel/ktask.holy` - cooperative tasks in ring 0 (policy in `.holy`, mechanism in the encoder):
  `spawn(func)` prepares stack+context for entry `f()`, `run()` round-robins
  until empty, `yield()` switches task-to-task directly, `exit()` ends a task;
  entries must end with `exit()` (a plain return gets scheduled again)
- mechanism in `x64gen.py`: `ctx_swap(save, load)`, `task_run(sched, task)`
  (remembers the way back for returning tasks), `task_init(ctx, top, func)`
  (sets r15=caps, rip=code, plants `task_exit` as the return address); the
  136-byte block holds all 15 GPRs + rsp + rip; the EXC report includes fault
  RIP + CR2
- preemption: a full-save stub calls `tick()` (read-only, no print/alloc)
  on the existing stack; returning Null = restore + iret, returning a block =
  the stub switches itself (the handler never swaps); `irq_off/on` brackets
  mutation, `sched_on_tick(f)`, a depth counter prevents nested ticks; the IDT
  uses interrupt gates, so `sti` is required before jumping into a task or it
  runs deaf
- `std.bitmap` - bit set over bytes (`bit_get/set/clear`, `reserve/release`,
  `bit_alloc_run`, `bit_take`, `bitmap_bytes`), runs on every backend

## filesystem (pure `.holy`)

A ramdisk from a multiboot module plus a truly editable VFS, all plain `.holy`
modules - no real block driver, data lives in RAM

- `kernel/kvfs.holy` - inodes kept as parallel lists (`v_names`/`v_parent`/`v_kind`/
  `v_data`); root = inode 0 and is its own parent; no cwd (every path
  resolves from root, leading `/` optional, `.`/`..` work): `mkdir`/`mkdirs`,
  `create`/`write`/`read`, `ls`, `stat` (`[kind, size]` or null),
  `is_file`/`is_dir`, `unlink` (dirs must be empty; an inode still open
  becomes dead and its fds go stale) plus an fd layer `fopen`/`fclose`/`fread`/`fwrite`/
  `fseek`/`ftell` - the `f*` names avoid clashing with the `open`/`read`/`write` builtins
- `kernel/kramdisk.holy` - unpacks the KRFS image the bootloader passes
  (`load_module(i)`, `load()` = module 0) into `kvfs`; reads only through
  `read_mem` and `kmb.rd32`, so no alignment assumptions
- `scripts/mkramdisk.py` - directory to image:
  ```sh
  python3 scripts/mkramdisk.py kernel/ramdisk /tmp/ramdisk.krfs
  qemu-system-x86_64 -kernel k.elf -initrd /tmp/ramdisk.krfs -serial stdio
  ```

  KRFS v1 (little-endian, every field padded up to 4 bytes) is `"KRFS"` | `u32`
  count | per entry: `u32` type (0 file, 1 directory) | `u32` path_len |
  path | pad | `u32` size | data | pad - ordered by path depth
  (parents before children), written in a single pass
- `kmb.holy` adds `mods_count()`/`mod_start(i)`/`mod_end(i)`/`mod_len(i)`
  (both multiboot ABIs) and `RUNTIME_BUMP_BASE`/`_SIZE`
- tests: `tests/t_vfs.holy` + `tests/x64/vfs.holy` (the whole VFS on interp/native/x64),
  `kernel/kfstest.holy` (real boot: loads the ramdisk, then reads/writes/deletes on QEMU)

## user mode + syscall (policy in `.holy`, mechanism in the encoder)

A user program is a static ELF64 from `python3 hs.py xbuild prog.holy`, passed
into the kernel as a multiboot module (`-initrd`) - no special runtime needed
because the backend already emits Linux-style syscalls (`write=1`, `mmap=9`, `exit=60`)

- `kernel/kuser.holy` - ELF loader: reads program headers, maps every `PT_LOAD` at
  its own address + `USER_BIAS` (user pages live in PML4 slot 1+; the kernel-side
  PML4[0] is supervisor-only and unreachable), W^X (text is `protect`ed
  read-only after copying), an 8-page stack; `run()` jumps into ring 3
- `kernel/ksyscall.holy` - `dispatch(nr, a1..a6)`: `sys_write` (fd 1/2 to
  serial via `read_mem`), `sys_mmap` (anonymous, kernel-chosen address),
  `sys_exit` (records the code then `user_stop()`); the exit code is opaque
  (already tagged, reused as is; Null becomes 0)
- mechanism in `x64gen.py`: the stub honors real `syscall` semantics - the CPU
  saves only rip->rcx and rflags->r11 (no frame, no stack switch), so the stub
  keeps return state with `xchg` (no scratch register needed) and moves itself
  to its own 16KB syscall stack (handlers can nest arbitrarily without
  overflowing the user stack); park/tag/handler/untag as before; the way back
  is `sysret` (never `iretq` - there is nothing to pop), while `user_stop()`
  returns through `user_cont_` on the existing stack
- the GDT has real user code/data (DPL=3 - not an OR-3 that only sets limit bits),
  a TSS (RSP0 for faults/IRQs from ring 3; `syscall` does not use it), `IA32_STAR`
  (the sysret half must point at base 0x10 so CS=0x20/SS=0x18 come back),
  `IA32_FMASK` (mask IF on entry), `EFER.SCE+LME`
- tests: `kring3` (exit via stop), `kring3ret` (sysret back to ring 3, then an
  hlt fault with USER rip + CS=0x23), `kring3wr` (write then exit),
  `kusermode` (a real ELF: prints/computes/exits back to the kernel)

## shell in ring 3 + file syscalls

User code reaches the VFS through the same syscall numbers as Linux (paths are
`(ptr, len)` with no NUL needed, because hs Strs have none):

| nr | syscall | what it does |
| --- | --- | --- |
| 0 | `read(fd, buf, len)` | fd 0 = keyboard (one line), others = file from kvfs |
| 1 | `write(fd, buf, len)` | fd 1/2 = serial, fd 3+ = file write |
| 2 | `open(path, len, flags)` | flags 0 = read, anything else = write (create/truncate) -> user fd = kvfs fd + 3 |
| 3 | `close(fd)` | |
| 59 | `exec(path, len)` | load an ELF from the VFS over the current image (once) |
| 78 | `ls(path, len, buf, max)` | directory entries separated by `\n` |
| 83 | `mkdir(path, len)` | create the whole path |
| 87 | `unlink(path, len)` | |

- `copy_out(dst, s, n)` copies a kernel Str into user memory (reflecting the
  real x64 pointer layout: `as_ptr(str) + 16` = payload); `n <= 0` returns 0
  immediately (so fd 0 never enters `readline()` and hangs)
- every pointer from ring 3 passes `user_range_ok(addr, n)` first: below
  `USER_BIAS` is kernel memory (or null) and must not be touched - returns
  `-EFAULT` (14) without any `read_mem`/`store8`; `kiotest` therefore pokes
  the path/buffer into a real user page (`map_user_pages`) instead of passing
  kernel addresses directly
- `write` on fd 1/2 is a serial line discipline, not byte-exact: `print`
  appends one `\n` the caller did not write (the return value still matches `n`)
- `readline()` on fd 0: `irq_on()` then spins on `readkey()` (this path is
  reached with IF=0, so keyboard IRQs would never arrive), backspace = byte 8
  (built once from `alloc` because hs escapes have no `\0..\8`), no echo
- `exec` calls `exec_enter` (an iretq that does not save a continuation), not
  `run()` - `run()` would overwrite the old session's continuation/stack and
  the new program could never return on exit
- `kernel/uush.holy` = a real ring-3 shell (`help echo cat ls mkdir rm write
  run exit`), talking to the kernel through `scall()`, newly added to the x64
  backend (hosted only - in ring 0 a `syscall` would return into ring 3 wrongly)
- Programs loaded by the kernel always see an empty `argv()`: `build_frame`
  plants argc=0 and argv[0]=NULL on top of the stack because the hosted
  `_start` reads argc from `[rsp]` following the Linux layout - without it the
  first user instruction would read an unmapped word and fault
- tests: `kiotest` (direct sys_open/read/write/close/copy_out without typing
  keys = deterministic), `kushtest` + two real shell sessions
  (`help`/`ls`/`cat`/backspace/`write`/`rm`/`exit` and `exec`)

## Current limitations

- Division by zero = CPU `#DE` -> `EXC 0` then halt (not catchable with try)
- The filesystem is pure RAM - still no persist across reboots; no multi-process
  user mode yet (one process + basic syscalls + one-shot `exec`, no fork/permissions)
- `ticks` starts counting after boot; the keyboard is scancode set 1 (no shift)

Tests: `python3 tests/test_xkernel.py` - real boots on QEMU (291 cases)


## Bounded keyboard FIFO

`readkey()` returns the oldest translated one-character Str, or null when
empty. IRQ1 queues up to 63 nonzero ASCII bytes in a 64-slot ring; beyond
that it drops newest bytes without replacing older input. Internal
`keydrops_` counts those software overflow drops modulo 2^64; it is not a
public builtin. Scancode translation remains set1 without shift/Unicode.
The consumer preserves the caller's IF flag, masks interrupts only for the
head update and restores flags before allocating the returned Str. This is
a single-CPU queue, not SMP synchronization or a general event subsystem.
Hardware overruns and input beyond capacity can still lose characters.

`tests/test_keyboard_queue.py` runs the actual generated helper code in QEMU
with deterministic bursts, wraparound, full/empty transitions, drop-newest
and IF=0/1 checks, followed by public `readkey()` String/null checks. It
injects translated bytes at the queue helper, not at the PS/2 hardware.
Existing keyboard/console QEMU tests separately cover actual IRQ input.
