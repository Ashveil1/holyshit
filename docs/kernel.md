# kernel freestanding (`hs.py xkernel`)

kernel เขียนด้วย `.hs` ล้วน ไม่มี C/asm ในสาย kernel —
assembler/linker x86-64 อยู่ใน `x64.py`, runtime อยู่ใน `x64gen.py`
(serial COM1, bump heap, IDT/PIC/PIT, `ticks`/`readkey`/PMM, ค่าแบบ tagged)

```sh
python3 hs.py xkernel kernel/xdemo.hs -o k.elf
qemu-system-x86_64 -kernel k.elf -serial stdio -display none
```

ตัวอย่างใน `kernel/`: `xdemo` (boot+fib), `kx2` (timer/keyboard/PMM),
`kxstr`/`kxlist`/`kxslice` (ค่าบน serial), `ktry` (try), `kimp` (import),
`kxexc_*` (EXC report)

## สิ่งที่มีบน kernel

- `print` ออก serial, `ticks()` 100Hz, `readkey()` คืนปุ่มล่าสุดหรือ Null
- `pmm_alloc(n)` / `pmm_total()` / `pmm_free()` (เพจ 4K เริ่ม 64MB)
- `unsafe:` เต็ม (`alloc`/`load`/`store`, struct) — คือวิธีแตะ hardware
- `import` ได้ (โมดูล `.hs` ธรรมดา), `try` ได้ (halt ถ้าไม่มี handler รับ)

## ข้อจำกัดตอนนี้

- หารด้วยศูนย์ = CPU `#DE` → `EXC 0` แล้ว halt (จับด้วย try ไม่ได้)
- ไม่มี paging แบบไดนามิก / scheduler / filesystem / user mode
  (ดู `SPEC-v1.md` หัวข้อ OS)
- `ticks` เริ่มนับหลังบูต; keyboard คือ scancode ชุด 1 (ไม่มี shift)

เทส: `python3 tests/test_xkernel.py` — บูตจริงบน QEMU (58 เคส)
