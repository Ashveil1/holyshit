# holyshit — วิสัยทัศน์ (VISION)

> เขียนเมื่อ 2026-10-12 ที่สถานะ **v0.6.30** จากเป้าหมายที่เจ้าของโปรเจกต์ (Ash) บอกไว้เอง
> แก้ครั้งที่ 2 หลังอ่านโค้ดจริง + รันเทส + วัด benchmark เทียบ CPython (ดู `docs/bench.md`)
> ไฟล์นี้คือ "เป้าหมายที่เปิดดูได้ทุกเมื่อ" — แผนลงมือทำอยู่ที่ [`ROADMAP.md`](ROADMAP.md)
>
> ป้ายในไฟล์นี้: **[เอกสาร]** = มีเขียนไว้ใน SPEC/docs/commit จริง ·
> **[วัดจริง]** = มีตัวเลขหรือเทสในรีโป · **[อนุมาน]** = ผู้เขียนเอกสารนี้สรุปเอง ยังไม่มีไฟล์ยืนยัน ·
> **[ยังไม่มี]** = ไม่พบในรีโป

## เป้าหมาย 7 ข้อ (คำของเจ้าของ สรุปสั้น)

holyshit (hs) จะเป็นภาษาที่:

1. **เร็วกว่า Python**
2. **ไม่ต้องคอมไพล์เอง — รันแบบ JIT** (เขียนแล้วรันทันที แต่เร็วระดับ native)
3. **เขียนง่ายกว่า Python**
4. **สร้าง OS ได้ด้วยตัวมันเอง** แทบไม่ต้องใช้ภาษาอื่น
5. **พึ่งตัวเองสมบูรณ์** (self-reliant: ไม่ต้องมี gcc/as/ld/libc, สุดท้าย compiler เขียนด้วย hs เอง)
6. **เข้ากันได้กับภาษาอื่น** — เรียกไลบรารีภาษาอื่นได้ (FFI)
7. **ออกแบบให้ AI เป็นคนเขียนเป็นหลัก** — ให้เป็นภาษาที่ AI เขียนได้ดีที่สุด

**ตัดออกจากเป้าหมาย (เจ้าของสั่ง 2026-10-12):** การใช้ไลบรารี Python ได้ครบสมบูรณ์ — ไม่ต้องทำ
(FFI ข้อ 6 ยังอยู่ แต่ไม่ต้องรองรับ CPython C-API / numpy ฯลฯ)

## สถานะต่อเป้าหมายแต่ละข้อ (ที่ v0.6.30)

### 1. เร็วกว่า Python — **เร็วกว่าในงาน int/เรียกฟังก์ชัน, มีจุดตายสองจุด**
- [วัดจริง] `docs/bench.md` (xbuild เทียบ CPython 3.10, เครื่อง sandbox 2 core): fib(32) 5.2x, loop 20M 6.4x,
  strings 2.1x, alloc 1.7x
- [วัดจริง] จุดตายที่พบ: (ก) dict ค้น key แบบ linear scan — 200k insert ใช้ 117 วินาที เทียบ CPython 0.1 วินาที
  (`emit_dict_helpers` ใน `x64gen.py`); แก้แล้วในคอมมิตหลัง baseline (hash index, ดู ROADMAP เฟส 1);
  (ข) ไม่มีการคืนหน่วยความจำบน x64 (bump allocator) — วน 5M รอบสร้าง string ใช้ 687 MB
- [เอกสาร] SPEC §10/§13 ตัวเลขเดิมเทียบกับ `interp.py` ไม่ใช่ CPython; `interp.py` ช้ากว่า CPython ~29x (fib 22: 436 ms vs 15 ms)
  จึงเป็นตัวอ้างอิงพฤติกรรมเท่านั้น
- [เอกสาร] ค่า tagged (Int 62-bit บน x64 ต่างจาก interp 64-bit), error check ทุก op (SPEC §13 วัดว่าทำให้ช้าลง),
  IR ยังไม่มี mem2reg/register allocation/optimizer

### 2. ไม่ต้องคอมไพล์ / JIT — **ยังไม่ทำ (มีแต่ฐาน)**
- [เอกสาร] `hs.py run` = build ลง temp แล้วรัน (ผ่าน gcc) ผู้ใช้ไม่เห็นขั้นตอน แต่ยังเป็นการคอมไพล์จริง
  และต้องมี gcc; `xbuild` ไม่ใช้ gcc แต่เขียนไฟล์ ELF ออกมา
- [เอกสาร] แผน IR ระบุ "JIT later" เป็นผู้ใช้ IR ในอนาคต (`docs/superpowers/plans/2026-10-08-ir-backend.md`)
- [ยังไม่มี] JIT จริง (สร้างโค้ดเครื่องในหน่วยความจำแล้วรันทันที), การ warm-up/tiering

### 3. เขียนง่ายกว่า Python — **มีหลักการ, ยังไม่มีตัววัด**
- [เอกสาร] SPEC หัวไฟล์: indent syntax, dynamic, ไม่ต้องประกาศ type, `print x` เป็น statement,
  งาน low-level อยู่ใน `unsafe:` เท่านั้น; tutorial/cheatsheet/ตัวอย่างรันได้
- [วัดจริง/อ่านเอกสาร] ภาษายังมีความสามารถน้อยกว่า Python: ไม่มี class/method (`",".join(x)` ใช้ไม่ได้ ต้อง `join(",", x)`), ไม่มี lambda, key ของ dict ต้องเป็น Str — ทำให้ AI ที่คุ้น Python เขียนพลาดและเป็นเหตุผลที่ "ง่ายกว่า" ยังไม่เป็นจริง
- [ยังไม่มี] นิยามว่า "ง่ายกว่า" วัดอย่างไร (เช่น จำนวน token/บรรทัดต่อโปรแกรมเทียบ Python,
  อัตราที่ AI/คนเขียนผ่านในรอบแรก)

### 4. สร้าง OS ด้วยตัวเอง — **ก้าวหน้าที่สุด**
- [วัดจริง] SPEC §15.8–§15.31: kernel `.hs` ล้วนบูตบน QEMU: paging + frame allocator, kmalloc/address space,
  cooperative → preemptive scheduler, ramdisk + VFS, ring-3 user mode + syscall, shell ring 3,
  port I/O, ATA PIO driver; `tests/test_xkernel.py` 291 เคส (ผ่านใน v0.6.29)
- [เอกสาร] ไม่มี C ในสาย kernel แล้ว (ลบ gcc path เมื่อ 2026-10-02)
- [วัดจริง, v0.6.30 บน sandbox ที่ไม่มี qemu] ชุดเทส interp/x64/IR/irx64/fmt/LSP/docs ผ่านทั้งหมด; ชุด native และ kernel (QEMU) รันไม่ได้ในเครื่องวัด จึงยังไม่ยืนยันเอง
- ช่องว่าง [ยังไม่มี/อนุมาน]: ไม่พบ network stack, filesystem บนดิสก์จริง (มีแค่ ramdisk/ATA ตัวแรก),
  ACPI/APIC/SMP, USB, กราฟิก, bootloader ของตัวเอง (ปัจจุบันบูตด้วย QEMU multiboot/ELF32 — ต้องตรวจ),
  การรันบนเครื่องจริง; kernel ยังใช้ backend ทาง AST เดิม ไม่ใช่ IR

### 5. พึ่งตัวเองสมบูรณ์ — **ครึ่งทาง**
- ทำแล้ว [เอกสาร]: assembler + ELF writer + linker เอง (`x64.py`), runtime เขียนเป็นโค้ดเครื่อง,
  float/JSON ไม่ใช้ libc, kernel ไม่ใช้ gcc/as/ld
- ยังพึ่ง [เอกสาร/อนุมาน]: ทั้ง toolchain เขียนด้วย **Python** (`interp.py` เป็น parser + reference,
  `hs.py`, `ir.py`, `x64gen.py`, `lsp.py`); โหมด `build` ยังใช้ gcc + Boehm GC;
  เทสใช้ QEMU; SPEC §15.35 เรียก IR ว่า "ก้าวแรกของแผน self-hosting"
- [วัดจริง/อ่านโค้ด] runtime ของ x64 (malloc, string, list, dict, float, JSON) ถูกเขียนเป็นโค้ด Python ที่ emit คำสั่งเครื่องทีละคำสั่ง (`x64gen.py` ~11k บรรทัด) — พอร์ตเป็น hs ตรง ๆ ไม่ได้ ต้องเขียน runtime ใหม่เป็น hs บน IR ก่อนจึง self-host ได้
- [ยังไม่มี] compiler ที่เขียนด้วย hs เอง (self-hosting), stdlib ที่ครบพอ (ไม่มี file/net/time/thread ครบ?
  — ต้องตรวจ `std/`), ตัวจัดการแพ็กเกจ

### 6. เข้ากันได้กับภาษาอื่น (FFI) — **มีแค่ C ABI บางส่วน**
- [เอกสาร] SPEC §11: `extern [from "lib"]` ผ่าน C ABI: ชนิด I64/U64/F64/Str/Ptr/U0; interp ใช้ ctypes,
  native ใช้ dlsym; ภาษาอื่นที่ export C ABI (Rust/Zig/C++/Go cgo) ใช้ได้ผ่าน `.so`
- ข้อจำกัด [เอกสาร]: ไม่มี struct, callback, variadic; ห้ามใน `unsafe` และใน kernel
- [ยังไม่มี/อนุมาน] extern บน x64 backend (SPEC §13–15 ลงว่ายังไม่มีที่ v0.6.14–15 — ต้องตรวจว่ามีแล้วหรือไม่),
  การเรียกกลับ hs จากภาษาอื่น, ตัวสร้าง binding อัตโนมัติ

### 7. AI เขียนเก่งที่สุด — **ฐานดี, ยังไม่มีการวัด**
- [เอกสาร] `AGENTS.md` (กฎกระชับ), `docs/for-agents.md`, `docs/api.json`, `docs/errors.md`,
  error แบบ JSON (`--json`: file/line/message), LSP (diag/hover/def/refs/sig) ผ่าน stdio ไม่มี dependency,
  เอกสารที่เทสตรวจว่าโค้ดตัวอย่างรันจริง (`tests/test_docs.py`)
- [ยังไม่มี] วัดว่า AI เขียน hs ได้ถูกแค่ไหน (eval suite), ภาษาเทียบกับ Python ที่โมเดลรู้อยู่แล้ว
  — ความเสี่ยง: ภาษาใหม่ไม่มีข้อมูลฝึก จึงต้องพึ่งเอกสาร/ตัวอย่าง/error ที่ดีมาก

## สถานะโดยรวม (ภาพเดียว)

| # | เป้าหมาย | ระดับตอนนี้ |
|---|---|---|
| 1 | เร็วกว่า Python | มีสัญญาณดี แต่ไม่มี benchmark เทียบ CPython |
| 2 | JIT | ยังไม่เริ่ม (IR เป็นฐาน) |
| 3 | ง่ายกว่า Python | หลักการมี ตัววัดไม่มี |
| 4 | สร้าง OS เอง | ก้าวหน้ามาก (kernel + user mode + shell + ATA) |
| 5 | พึ่งตัวเอง | ครึ่งทาง: ไม่ใช้ gcc ใน xbuild/kernel แต่ toolchain ยังเป็น Python |
| 6 | FFI | C ABI บางส่วน |
| 7 | AI-first | ฐานดี ไม่มีการวัด |

## ความขัดแย้งในตัวเป้าหมาย (ต้องตัดสินใจ — ดู ROADMAP "ความเสี่ยง")

- **JIT + ไม่ต้องคอมไพล์ vs พึ่งตัวเองสมบูรณ์:** JIT ต้องมีตัวสร้างโค้ดเครื่องที่รันใน process เดียวกัน
  (ทำได้ เพราะมี encoder `x64.py` อยู่แล้ว) แต่ถ้าเขียนด้วย Python ก็ยังพึ่ง Python อยู่ — ต้อง self-host ก่อนถึงจะ "พึ่งตัวเอง" จริง
- **เร็วกว่า Python vs ข้อความ error ละเอียด + tagged value:** SPEC §13 วัดแล้วว่า error check ทำให้ช้าลง
- **ง่ายกว่า Python (dynamic) vs เร็ว (static):** dynamic ทั้งหมดทำให้ JIT ต้องมี type feedback/specialization
- **ใช้ทุกอย่างได้เหมือนทุกภาษา vs ตัดไลบรารี Python:** เจ้าของตัดข้อหลังออกแล้ว ใช้ FFI แทน
