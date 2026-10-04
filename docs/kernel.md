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
`kxexc_*` (EXC report), `kprim` (primitives), `kpaging` (paging),
`kpmmtest` (frame allocator)

## สิ่งที่มีบน kernel

- `print` ออก serial, `ticks()` 100Hz, `readkey()` คืนปุ่มล่าสุดหรือ Null
- `pmm_alloc(n)` / `pmm_total()` / `pmm_free()` (เพจ 4K เริ่ม 64MB — ของเก่า,
  โค้ดจริงใช้ `kpmm` ข้างล่าง)
- boot info: `mb_info()` (struct ของ bootloader), `mb_magic()` (magic จาก EAX),
  `image_end()` (address แรกหลัง kernel image — PMM reserve ถึงตรงนี้)
- paging: `cr2()`/`cr3()`/`set_cr3(p)`, `invlpg(vaddr)`, `tlb_flush()`
- `unsafe:` เต็ม (`alloc`/`load`/`store` incl. `load64`/`store64`, struct) —
  คือวิธีแตะ hardware
- `import` ได้ (โมดูล `.hs` ธรรมดา), `try` ได้ (halt ถ้าไม่มี handler รับ)

## memory management (`.hs` ล้วน)

- `kernel/kmb.hs` — อ่าน memory map ของ bootloader รองรับ 2 แบบ (ตรวจโดย
  validate ไม่ใช่เชื่อค่า EBX): spec multiboot1 กับ struct 88-byte ของ QEMU
  เอง (layout ไม่ตรง spec — ดู source `hw/i386/multiboot.c` ของ QEMU)
- `kernel/kpage.hs` — page table 4 ระดับ: `map`/`unmap`/`translate`,
  `is_mapped`, `map_phys`/`map_user`; สร้างตารางที่ขาดอัตโนมัติ, แยก huge
  page (2MB/1GB) เป็นลูก 512 ตัวเมื่อต้อง map 4K ข้างใน, flush TLB ทุกครั้ง
- `kernel/kpmm.hs` — frame allocator จริงบน bitmap (`std.bitmap`):
  เอาเฟรมจาก region  usable ที่ใหญ่สุด, reserve image/heap/bitmap ตัวเอง,
  `alloc(n)` คืน address 4K-aligned, `free`/`free_run` คืน pool
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

## ข้อจำกัดตอนนี้

- หารด้วยศูนย์ = CPU `#DE` → `EXC 0` แล้ว halt (จับด้วย try ไม่ได้)
- ยังไม่มี filesystem / user mode (ดู `SPEC-v1.md` หัวข้อ OS)
- `ticks` เริ่มนับหลังบูต; keyboard คือ scancode ชุด 1 (ไม่มี shift)

เทส: `python3 tests/test_xkernel.py` — บูตจริงบน QEMU (99 เคส)
