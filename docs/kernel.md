# kernel freestanding (`hs.py xkernel`)

kernel เขียนด้วย `.hs` ล้วน ไม่มี C/asm ในสาย kernel —
assembler/linker x86-64 อยู่ใน `x64.py`, runtime อยู่ใน `x64gen.py`
(serial COM1, bump heap, IDT/PIC/PIT, `ticks`/`readkey`, ค่าแบบ tagged)

```sh
python3 hs.py xkernel kernel/xdemo.hs -o k.elf
qemu-system-x86_64 -kernel k.elf -serial stdio -display none
```

ตัวอย่างใน `kernel/`: `xdemo` (boot+fib), `kx2` (timer/keyboard/PMM),
`kxstr`/`kxlist`/`kxslice` (ค่าบน serial), `ktry` (try), `kimp` (import),
`kxexc_*` (EXC report), `kprim` (primitives), `kpaging` (paging)
โมดูลจริง: `kmb` `kpage` `kpmm` `kheap` `kaddr` `ktask` `kvfs` `kramdisk`
`ksyscall` `kuser` (user program ตัวอย่าง: `uuser`, shell: `uush`)
เทสใน QEMU: `kpmmtest` `kheaptest` `kaddrtest` `ktasktest` `kpreempt`
`kfstest` `kring3` `kring3ret` `kring3wr` `kusermode` `kiotest` `kushtest`

## สิ่งที่มีบน kernel

- `print` ออก serial, `ticks()` 100Hz, `readkey()` คืนปุ่มล่าสุดหรือ Null
- `pmm_alloc(n)` / `pmm_total()` / `pmm_free()` (เพจ 4K เริ่ม 64MB — ของเก่า,
  โค้ดจริงใช้ `kpmm` ข้างล่าง)
- boot info: `mb_info()` (struct ของ bootloader), `mb_magic()` (magic จาก EAX),
  `image_end()` (address แรกหลัง kernel image: โค้ด + `.data` ที่มี main
  stack + page tables ตอนบูต — PMM reserve ถึงตรงนี้, เกินไปแล้ว bootloader
  เขียนทับของเรา)
- `read_mem(ptr, n)` — อ่าน memory ดิบเป็น Str (ไบต์ต่อไบต์) ใช้อ่าน struct
  ของ bootloader กับ image ramdisk
- paging: `cr2()`/`cr3()`/`set_cr3(p)`, `invlpg(vaddr)`, `tlb_flush()`
- `unsafe:` เต็ม (`alloc`/`load`/`store` incl. `load64`/`store64`, struct) —
  คือวิธีแตะ hardware
- `import` ได้ (โมดูล `.hs` ธรรมดา), `try` ได้ (halt ถ้าไม่มี handler รับ)

## memory management (`.hs` ล้วน)

- `kernel/kmb.hs` — อ่าน memory map ของ bootloader รองรับ 2 แบบ (ตรวจโดย
  validate ไม่ใช่เชื่อค่า EBX): spec multiboot1 กับ struct 88-byte ของ QEMU
  เอง (layout ไม่ตรง spec — ดู source `hw/i386/multiboot.c` ของ QEMU)
- `kernel/kpage.hs` — page table 4 ระดับ: `map`/`unmap`/`translate`,
  `is_mapped`, `map_phys`/`map_user`, `protect` (เปลี่ยน permission ทีหลัง
  ใช้ทำ user text read-only); สร้างตารางที่ขาดอัตโนมัติ, แยก huge
  page (2MB/1GB) เป็นลูก 512 ตัวเมื่อต้อง map 4K ข้างใน, flush TLB ทุกครั้ง;
  map แบบ user พา U/S bit ลงไปทั้ง path (ตารางชั้นกลางของ kernel เป็น
  supervisor — ไม่ทำ ring 3 จะ fault ตั้งแต่ iret แรก)
- `kernel/kpmm.hs` — frame allocator จริงบน bitmap (`std.bitmap`):
  เอาเฟรมจาก region usable ที่ใหญ่สุด, reserve image/หน้าต่างบูต/heap/
  bitmap ตัวเอง, `alloc(n)` คืน address 4K-aligned, `free`/`free_run` คืน
  pool, `busy(paddr)` ถามว่าเฟรมนั้นถูกจองอยู่
- `kernel/kheap.hs` — kmalloc (`std.heap` K&R malloc/free) บนเฟรมจริงที่ map
  ไว้ที่ `0x60000000`: `init(npages)`, `malloc`/`free`, `free_bytes`
- `kernel/kaddr.hs` — address space ละหนึ่ง PML4 แชร์ mapping ฝั่ง kernel
  (PML4[0]); `new`/`switch`/`current`; user page ต้องอยู่ `>= 0x8000000000`
  (PML4 slot 1+) จึงจะ isolated จริง
- `kernel/ktask.hs` — cooperative task ใน ring 0 (policy `.hs`, กลไก encoder):
  `spawn(func)` เตรียม stack+context ให้ entry `f()`, `run()` วน round-robin
  จนหมด, `yield()` สลับตรง task→task, `exit()` จบ task; entry ต้องจบด้วย
  `exit()` (return เฉยๆ จะถูก schedule ซ้ำ)
- mechanism ใน `x64gen.py`: `ctx_swap(save, load)`, `task_run(sched, task)`
  (จำทางกลับให้ task ที่ return), `task_init(ctx, top, func)` (เซ็ต r15=caps,
  rip=code, วาง `task_exit` เป็น return address); block 136 bytes เก็บครบ
  15 GPRs + rsp + rip; EXC report มี fault RIP + CR2 แล้ว
- preemption: stub เซฟเต็ม + เรียก `tick()` (อ่านอย่างเดียว ห้าม print/alloc)
  บน stack เดิม; คืน Null = restore + iret, คืน block = switch เองใน stub
  (handler ไม่ swap เอง); `irq_off/on` ครอบ mutation, `sched_on_tick(f)`,
  depth counter กัน nested tick; IDT เป็น interrupt gate จึงต้อง `sti` ก่อน
  กระโดดเข้า task ไม่งั้นวิ่งแบบหูหนวก
- `std.bitmap` — bit set บน byte (`bit_get/set/clear`, `reserve/release`,
  `bit_alloc_run`, `bit_take`, `bitmap_bytes`) รันได้ทุก backend

## filesystem (`.hs` ล้วน)

ramdisk จาก multiboot module + VFS ที่แก้ไฟล์ได้จริง ทั้งหมดเป็นโมดูล `.hs`
ธรรมดา — ไม่มี block driver จริง, ข้อมูลอยู่ใน RAM

- `kernel/kvfs.hs` — inode เก็บเป็นลิสต์ขนาน (`v_names`/`v_parent`/`v_kind`/
  `v_data`), root = inode 0 และเป็น parent ของตัวเอง, ไม่มี cwd (ทุก path
  resolve จาก root, `/` นำหน้าไม่บังคับ, `.`/`..` ได้): `mkdir`/`mkdirs`,
  `create`/`write`/`read`, `ls`, `stat` (`[kind, size]` หรือ null),
  `is_file`/`is_dir`, `unlink` (dir ต้องว่าง; inode ที่ยังเปิดอยู่ถูกทำ
  เป็น dead แล้ว fd จะ stale) และ fd layer `fopen`/`fclose`/`fread`/`fwrite`/
  `fseek`/`ftell` — ชื่อ `f*` กันชนกับ builtin `open`/`read`/`write`
- `kernel/kramdisk.hs` — แกะ KRFS image ที่ bootloader ส่งมา
  (`load_module(i)`, `load()` = module 0) เข้า `kvfs`; อ่านด้วย `read_mem`
  กับ `kmb.rd32` เท่านั้น จึงไม่ต้องพึ่ง alignment
- `scripts/mkramdisk.py` — จาก directory สู่ image:
  ```sh
  python3 scripts/mkramdisk.py kernel/ramdisk /tmp/ramdisk.krfs
  qemu-system-x86_64 -kernel k.elf -initrd /tmp/ramdisk.krfs -serial stdio
  ```

  KRFS v1 (little-endian, field ทุกตัว pad ขึ้น 4 ไบต์) คือ `"KRFS"` | `u32`
  count | ต่อ entry: `u32` type (0 ไฟล์, 1 ไดเรกทอรี) | `u32` path_len |
  path | pad | `u32` size | data | pad — เรียงตามความลึกของ path
  (parent มาก่อนลูก) แก้ทีเดียวเป็น pass เดียว
- `kmb.hs` เพิ่ม `mods_count()`/`mod_start(i)`/`mod_end(i)`/`mod_len(i)`
  (multiboot module ทั้งสอง ABI) และ `RUNTIME_BUMP_BASE`/`_SIZE`
- เทส: `tests/t_vfs.hs` + `tests/x64/vfs.hs` (VFS ทั้งชุดบน interp/native/x64),
  `kernel/kfstest.hs` (บูตจริง: โหลด ramdisk แล้วอ่าน/แก้/ลบบน QEMU)

## user mode + syscall (`.hs` ล้วน, กลไก encoder)

โปรแกรม user คือ static ELF64 จาก `python3 hs.py xbuild prog.hs` ส่งเข้า
kernel เป็น multiboot module (`-initrd`) — ไม่ต้องมี runtime พิเศษเพราะ
backend ส่ง syscall แบบ Linux อยู่แล้ว (`write=1`, `mmap=9`, `exit=60`)

- `kernel/kuser.hs` — โหลด ELF: อ่าน program header, map ทุก `PT_LOAD` ที่
  address ของตัวเอง + `USER_BIAS` (user page อยู่ PML4 slot 1+ ฝั่ง kernel
  PML4[0] เป็น supervisor-only แตะไม่ถึง), W^X (text ให้ `protect` เป็น
  read-only หลัง copy), stack 8 เพจ; `run()` กระโดดเข้า ring 3
- `kernel/ksyscall.hs` — `dispatch(nr, a1..a6)`: `sys_write` (fd 1/2 ออก
  serial ผ่าน `read_mem`), `sys_mmap` (anonymous ที่ kernel เลือกให้),
  `sys_exit` (จำ code แล้ว `user_stop()`); exit code เป็น opaque (tagged
  อยู่แล้วใช้เลย, Null กลายเป็น 0)
- กลไกใน `x64gen.py`: stub รับ `syscall` ตาม semantics จริง — CPU เซฟแค่
  rip→rcx กับ rflags→r11 (ไม่มี frame, ไม่สลับ stack) ดังนั้น stub เก็บ
  return state ด้วย `xchg` (ไม่ต้องใช้ scratch) แล้วย้ายเองไป syscall
  stack 16KB ของตัวเอง (handler ลึกแค่ไหนก็ไม่ล้น user stack);
  park/tag/handler/untag เหมือนเดิม ขากลับคือ `sysret` (ห้าม `iretq` —
  ไม่มีอะไรให้ pop) ส่วน `user_stop()` กลับทาง `user_cont_` บน stack เดิม
- GDT มี user code/data (DPL=3 จริง — ไม่ใช่ OR 3 ที่ได้แค่ limit bits),
  TSS (RSP0 รับ fault/IRQ จาก ring 3; `syscall` ไม่ใช้), `IA32_STAR`
  (ครึ่ง sysret ต้องชี้ base 0x10 จึงได้ CS=0x20/SS=0x18 กลับมา),
  `IA32_FMASK` (mask IF ตอนเข้า), `EFER.SCE+LME`
- เทส: `kring3` (exit ผ่าน stop), `kring3ret` (sysret กลับ ring 3 แล้ว hlt
  fault ด้วย USER rip + CS=0x23), `kring3wr` (write แล้ว exit),
  `kusermode` (ELF จริง: พิมพ์/คำนวณ/exit กลับมา kernel ครบ)

## shell ใน ring 3 + syscall ไฟล์

user ต่อกับ VFS ผ่าน syscall ตัวเลขเดียวกับ Linux (path แบบ
`(ptr, len)` ไม่ต้องมี NUL เพราะ Str ของ hs ไม่มี):

| nr | syscall | ทำอะไร |
| --- | --- | --- |
| 0 | `read(fd, buf, len)` | fd 0 = keyboard (หนึ่งบรรทัด), อื่น ๆ = ไฟล์จาก kvfs |
| 1 | `write(fd, buf, len)` | fd 1/2 = serial, fd 3+ = เขียนไฟล์ |
| 2 | `open(path, len, flags)` | flags 0 = อ่าน, อื่น ๆ = เขียน (สร้าง/ตัด) → fd ของ user = kvfs fd + 3 |
| 3 | `close(fd)` | |
| 59 | `exec(path, len)` | โหลด ELF จาก VFS ทับ image เดิม (ครั้งเดียว) |
| 78 | `ls(path, len, buf, max)` | รายชื่อใน dir คั่นด้วย `\n` |
| 83 | `mkdir(path, len)` | สร้างทั้ง path |
| 87 | `unlink(path, len)` | |

- `copy_out(dst, s, n)` คัดลอก Str ของ kernel ลง user memory (สะท้อน
  pointer ความจริงของ x64: `as_ptr(str) + 16` = payload); `n <= 0` คืน 0
  ทันที (fd 0 จะได้ไม่เข้า `readline()` แล้วค้าง)
- ทุก pointer จาก ring 3 ผ่าน `user_range_ok(addr, n)` ก่อน: ต่ำกว่า
  `USER_BIAS` คือ kernel memory (หรือ null) ห้ามแตะ — คืน `-EFAULT` (14)
  โดยไม่ `read_mem`/`store8` เลย; `kiotest` เลยต้อง poke path/buffer ลง
  user page จริง (`map_user_pages`) แทนที่จะส่ง kernel address ตรง ๆ
- `write` fd 1/2 เป็น serial line discipline ไม่ใช่ byte-exact: `print`
  แถม `\n` หนึ่งตัวที่ caller ไม่ได้เขียน (return value ยังตรง `n`)
- `readline()` บน fd 0: `irq_on()` แล้ว spin `readkey()` (path นี้มาแบบ
  IF=0 คีย์บอร์ดจะไม่มาให้), backspace = byte 8 (สร้างครั้งเดียวจาก
  `alloc` เพราะ hs escape ไม่มี `\0..\8`), ไม่ echo
- `exec` เรียก `exec_enter` (iretq แบบไม่บันทึก continuation) ไม่ใช่
  `run()` — ถ้าใช้ `run()` มันจะทับ continuation/stack ของ session เดิม
  แล้วพอโปรแกรมใหม่ exit ก็กลับไปไม่ได้
- `kernel/uush.hs` = shell จริงใน ring 3 (`help echo cat ls mkdir rm write
  run exit`), คุยกับ kernel ผ่าน `scall()` ที่เพิ่มใหม่ใน x64 backend
  (hosted only — ring 0 เรียก `syscall` แล้วขากลับตกลงไป ring 3 ผิด)
- เทส: `kiotest` (sys_open/read/write/close/copy_out ตรง ๆ ไม่ต้อง
  พิมพ์คีย์ = deterministic), `kushtest` + shell session จริงสองรอบ
  (`help`/`ls`/`cat`/backspace/`write`/`rm`/`exit` และ `exec`)

## ข้อจำกัดตอนนี้

- หารด้วยศูนย์ = CPU `#DE` → `EXC 0` แล้ว halt (จับด้วย try ไม่ได้)
- filesystem เป็น RAM ล้วน — ยังไม่มี block driver/ATA และยังไม่ persist
  ข้าม reboot; ยังไม่มี user mode หลายโปรเซส (โปรเซสเดียว + syscall
  พื้นฐาน + `exec` แบบครั้งเดียว, ยังไม่มี fork/permissions)
- `ticks` เริ่มนับหลังบูต; keyboard คือ scancode ชุด 1 (ไม่มี shift)

เทส: `python3 tests/test_xkernel.py` — บูตจริงบน QEMU (274 เคส)
