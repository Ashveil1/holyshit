# holyshit — แผนงาน (ROADMAP)

> เขียนเมื่อ 2026-10-12 จากสถานะ **v0.6.30** เพื่อไปให้ถึงเป้าหมายใน [`VISION.md`](VISION.md)
> แก้ครั้งที่ 2 หลังอ่านโค้ด/รันเทส/วัด benchmark จริง: ตัวเลขอยู่ที่ [`bench.md`](bench.md)
> ป้าย: **[เอกสาร]** = มีเขียนไว้ในรีโป · **[อนุมาน]** = สมมติฐานของผู้เขียนแผน ต้องยืนยันกับเจ้าของ/โค้ด ·
> ลำดับและเวลาเป็นข้อเสนอ ไม่ใช่คำมั่น (ไม่มี roadmap เดิมหลัง v0.6.30 ในรีโป นอกจากแผน IR)
>
> หลักการ: ทุกเฟสต้องมี **เกณฑ์ผ่านที่รันได้** (คำสั่ง + ผลที่คาด), เทสเดิมต้องเขียวตลอด
> (`python3 tests/run_all.py`), ทุกการเปลี่ยนมี benchmark ตามด้วย

## สถานะล่าสุด (วัดจริง, เทสเขียวใน CI เต็ม)

| เป้า | หลักฐาน | ประเมิน |
|---|---|---|
| เร็วกว่า Python | `bench/run.py` ด้านล่าง: loop/fib ~5-6x, alloc 2.6x, dict 1.3-1.5x, strings 1.3-1.5x (ช่วงจากหลายรอบ) | ~65% |
| JIT / ไม่มีขั้นตอน compile | `hs run` ใช้ x64 เป็นค่าเริ่มต้น (build+รัน ~0.1 s ไม่ใช้ gcc; รันซ้ำซอร์สเดิม/คอมไพเลอร์เดิมใช้ binary จาก cache: โปรแกรม ~1900 บรรทัด 0.45s → 0.045s, ปิดด้วย HS_RUN_CACHE=off) fallback เองเมื่อนอก subset / Int เกิน 62-bit | ~55% |
| ง่ายกว่า Python | f-string, lambda, class/inherit, `in`, ternary, keys/values/has, prelude (abs/min/max/sum/sorted/...; cc ก็มีแล้ว), stack overflow เป็น error สะอาด; assert + list comprehension มีแล้ว; enumerate + `for i, x in` มีแล้ว; default args (def f(a, b=expr)) มีแล้ว | ~60% |
| พึ่งตัวเองได้ | x64 + kernel + FFI ไม่ใช้ gcc; lexer/parser/formatter เขียนด้วย hs ตรงกับ Python ทุกไบต์บนไฟล์ในรีโป (808 เช็ค) และ parse ตัวเองได้; `selfhost/cc.hs` = compiler เขียนด้วย hs (parse ด้วย parselib.hs → ELF x86-64 ตรงด้วย `write_bytes`, subset Int/def/recursion/while/print) ผลตรง interp 24 เคส; ยังเล็ก (ไม่มี list/str/dict/float) ต้องขยายจนคอมไพล์ตัวเองได้ ; **bootstrap fixed point**: cc.hs (ผ่าน interp) → cc2 (ELF) → cc3 โดย cc2 == cc3 ไบต์ต่อไบต์ (test_cc 79 เคส; cc รองรับ ternary + default args + closure/lambda/listcomp ที่จับค่าตอน def) และ `hs cc prog.hs` ใช้ compiler ที่เขียนด้วย hs นี้; subset ยังไม่มี Float/class/GC/FFI (cc corpus ผ่าน 15/44, class+inherit ใช้ได้ (bound method เป็นค่ายังไม่รองรับ) แล้ว) ไม่แทน x64gen/irx64 ทั้งหมด | ~60% |
| FFI | native + x64 (I64/U64/Ptr/Str/F64); struct by pointer ผ่าน malloc+load/store (เทสกับ gmtime_r ตรงกัน interp/native/x64); ยังไม่มี struct by value/callback | ~57% |
| เขียน OS ด้วยตัวเอง | kernel บูตบน QEMU, xkernel 291 เคส (VFS, shell ring3, paging, preempt, float, JSON) | ~70% |
| AI-first | error แบบมีโครงสร้าง (`--json`), LSP, docs/api.json, `hs fmt` (เก็บคอมเมนต์แล้ว); `hs test` (test runner, `--json`) มีแล้ว; `hs repl` มีแล้ว; `hs explain "<error>"` หรือ `hs explain E004` (ความหมาย+วิธีแก้ จาก errors.md, `--json`); error ที่เจอบ่อย 12 ตัวมีรหัส E001-E012 และ `--json` (check/build/run, รวม runtime error) ใส่ `code`+`hint` ให้; evals/ มีชุดโจทย์ 39 ข้อ + checker อัตโนมัติ (ยังไม่ได้รันกับโมเดล จึงยังไม่มี pass@1) | ~45% |

ภาพรวม ~60% (ยังไม่ถึง 80%) ส่วนที่ใหญ่ที่สุดที่เหลือ: code generator ใน hs (self-host เต็ม), JIT จริง, GC ให้เร็วขึ้นเมื่อ live heap ใหญ่ (strings/alloc/dict)

```
case          cpython  hs xbuild    ratio   MB py   MB hs  output
alloc          0.967s     0.405s    2.39x       9      16  same
dict           0.083s     0.065s    1.29x      39      27  same
fib            0.325s     0.093s    3.50x       9       9  same
loop           1.506s     0.246s    6.13x       9       9  same
strings        0.778s     0.627s    1.24x     443     469  same
```

## เส้นทางสู่ self-host เต็ม (compiler ใน hs คอมไพล์ตัวเองได้)

สถานะ: `selfhost/cc.hs` ผ่าน M1-M5 ครบสำหรับ subset (bootstrap fixed point พิสูจน์ใน tests/test_cc.py). ที่เหลือคือขยาย subset จนแทน x64gen/irx64 (Float, class, GC, FFI, kernel) ซึ่งยัง **ใหญ่** — แบ่งเป็นขั้นด้านล่าง

| ขั้น | เนื้อหา | เกณฑ์ผ่าน (รันได้) |
|---|---|---|
| M1 ✔ | Int, def/recursion, while/if, print Int/str literal → ELF | test_cc 24 เคส, ELF จาก interp = จาก native |
| M1.5 ✔ | `selfhost/asm.hs`: assembler เขียนด้วย hs (subset จำนวนเต็มของ x64.py) | test_asm: ไบต์ตรง x64.py 17.8k คำสั่ง |
| M2 ✔ | ค่าแบบ tagged (Int 63 บิต/Bool/Null/Str/List/Dict), heap bump (ไม่มี GC), str + len index == < print, list literal/append/get/set/for/==, dict literal/get/set/in/keys/values/== ที่ emit จาก hs | test_cc 56 เคส: stdout ตรง interp + error ออก exit≠0 เหมือนกัน |
| M3 ✔ | import (flatten โมดูล), slice, str(), try/except/raise, argv/read_text/write_bytes/find/split/int, for บน Str/Dict | cc.hs คอมไพล์ parselib+lexlib+asm+cc ทั้งชุดได้ |
| M4 ✔ | builtins ที่ cc.hs ใช้เอง | cc.hs (ผ่าน interp) คอมไพล์ cc.hs → ELF cc2 (275KB) ที่รันได้ คอมไพล์โปรแกรมทดสอบทั้งหมดได้ไบต์ตรง cc1 |
| M5 ✔ | bootstrap: cc1 (cc.hs รันด้วย interp) → cc2 (ELF) → cc3; cc2 == cc3 ไบต์ต่อไบต์ | test_cc "bootstrap: fixed point" (cc2 คอมไพล์ cc.hs ใน 0.4 วิ เทียบ ~10 วิ ด้วย interp) |

**ขอบเขตที่พิสูจน์แล้ว**: คอมไพเลอร์ subset (cc.hs) ทำ fixed-point ได้ แต่ subset นี้ยังไม่มี Float, class, closure/lambda ใน runtime (lambda desugar ที่ parse ได้), GC (bump heap 1GB), Int แค่ 63 บิต (literal >= 2^61 ต้องใช้ cc1), dict ค้นแบบเชิงเส้น, error จาก runtime จับด้วย try ไม่ได้ (raise string จับได้). `hs` ตัวเต็ม (x64gen/irx64 ใน Python, native ผ่าน gcc, FFI, kernel) ยังไม่ถูก port — จึงยังไม่ claim ว่า "พึ่งตัวเองเต็ม"

## ที่วัดได้ก่อนเริ่ม (v0.6.30, ดู `bench.md`)

- เทส interp/x64/IR/irx64/fmt/LSP/docs ผ่านทั้งหมด; native และ kernel (QEMU) รันไม่ได้ในเครื่องวัด → ให้ CI ยืนยัน
- xbuild เร็วกว่า CPython 5-6x ในงาน int/เรียกฟังก์ชัน
- dict 200k insert: 117 s (CPython 0.1 s) เพราะ linear scan; วน alloc 5M รอบ: 687 MB เพราะไม่มี free
- ภาษายังขาด class/method/lambda และ dict key ที่ไม่ใช่ Str

## เฟส 0 — พื้นฐานให้ไว้ใจได้ (ทำแล้ว)

| งาน | สถานะ |
|---|---|
| CI (`.github/workflows/ci.yml`): quick ทุก push/PR; ทุกคืน = ชุดเต็ม + QEMU + bench | ทำแล้ว (ต้องดูผลรันแรกบน GitHub) |
| `bench/` คู่ .hs/.py + `bench/run.py` + `docs/bench.md` baseline | ทำแล้ว |
| sync เลขเวอร์ชัน/จำนวนเทสใน README/AGENTS/run_all | ทำแล้ว |
| tag `v0.6.30` | ทำที่ commit baseline |
| LICENSE | **ยังไม่ทำ** รอเจ้าของเลือก |

## เฟส 1 — จุดตายด้านความเร็ว/หน่วยความจำ (กำลังทำ)  [เป้า 1, 5]

1. **hash dict บน x64 (ทำแล้ว):** dict ที่มี ≥ 8 key สร้างตาราง hash (FNV-1a, open addressing, load ≤ 0.5) ข้างอาร์เรย์คู่ key/value เดิม
   (ลำดับ insertion คงเดิม; dict เล็กยังเป็น linear scan) — 200k insert: 117 s → 0.05 s (CPython 0.08 s); เทส `tests/dict_hash.hs` เทียบ interp
2. **ตัวคืนหน่วยความจำ:** free list อย่างเดียวช่วยไม่ได้เพราะไม่มีใครรู้ว่าอะไรตาย จึงต้องมี GC —
   แผน: mark-sweep แบบ conservative, รันเฉพาะ "จุดปลอดภัย" ที่ IR backend emit (หัวฟังก์ชัน/loop back-edge) เพื่อไม่ให้ helper ของ runtime
   ค้างกลางทาง, header 16 ไบต์ต่อ block + bitmap จุดเริ่ม block ต่อ arena, block ของ `unsafe` ที่ `x_alloc` ถูก pin ไม่เก็บ
   เกณฑ์ผ่าน: `bench/alloc` ใช้ < 50 MB, ทุกชุดเทสเขียว, เทส stress (list/dict/closure/exception ซ้อนกัน) เทียบ interp;
   ถ้าทำให้มั่นคงไม่ได้ให้ revert และเก็บเป็นงานของเฟส 3 (runtime ใหม่เป็น hs)

## เฟส 2 — ย้าย kernel ไป IR และปิด backend AST เก่า (1–2 สัปดาห์)  [เป้า 4, 5]

เหตุผล [เอกสาร]: SPEC §15.35/15.38: `xkernel` ยังใช้ `x64gen.build_x64_ast`; `xbuild` ใช้ IR แล้ว (v0.6.28)

1. เพิ่ม lowering ของ freestanding (serial, heap, IDT, PIT, port I/O, `unsafe`) ใน `irx64.py`
2. รัน kernel corpus (`kernel/*.hs`, 291 เคส) ผ่าน IR path เทียบกับ AST path แบบ ELF-ต่อ-ELF + QEMU
3. สลับ `hs.py xkernel` ไป IR; เก็บ AST path ไว้หลัง flag 1 รุ่น แล้วลบ
4. ให้ IR path ผ่านการเดินคอร์ปัสทั้งหมดอย่างที่ v0.6.30 ทำกับ `xbuild` (หาบั๊กแบบที่เจอ 5 ข้อ)

**เกณฑ์ผ่าน:** `test_xkernel.py` 291/291 บน IR path; ลบ `build_x64_ast` ได้โดยเทสเขียว; bench kernel boot ไม่ช้าลง

## เฟส 3 — ความสามารถของภาษา + optimizer (4–6 สัปดาห์)  [เป้า 1, 3, 7]

ภาษายังขาดสิ่งที่ AI/คนคุ้นจาก Python: method บน builtin (`s.split(",")`, `l.append(x)`, `d.get(k)`), lambda, key ของ dict ที่ไม่ใช่ Str, class/struct พร้อม method, string formatting.
ทุกฟีเจอร์ต้อง: เขียน SPEC ก่อน, เปลี่ยน `interp.py` ก่อน (ต้นแบบพฤติกรรม), แล้วตามด้วย IR/x64/native พร้อมเทสเทียบ

[เอกสาร] ปัจจุบัน: ค่า tagged (Int 62-bit), bump allocator ไม่ free บน x64, Boehm GC บน native

- 3.1 ถ้า GC ในเฟส 1 ไม่ผ่าน: ตัวจัดสรร + GC เขียนด้วย hs/IR (runtime ใหม่) — จำเป็นสำหรับโปรแกรมยาว, kernel, JIT และ self-host
- 3.2 optimization บน IR: constant folding, dead code, inline ฟังก์ชันเล็ก, mem2reg (plan IR บอกว่าเลื่อนไว้)
  [เอกสาร: "ตัวแปรไม่ทำ mem2reg ตั้งแต่…"] — ทุกตัวต้องรักษา "ผลตรง interp ทุกไบต์"
- 3.3 register allocation แบบง่าย (linear scan) แทนการใช้ stack ทุกตัว **[อนุมาน — ต้องดู x64gen ว่าทำอย่างไรตอนนี้]**
- 3.4 แก้ divergence ที่จดไว้: Int 62-bit บน x64 vs 64-bit บน interp ตัดสินใจเลือกอย่างใดอย่างหนึ่ง (bigint/overflow semantic)
- **เกณฑ์ผ่าน:** bench เฟส 1 ดีขึ้นตามเป้าและไม่มี regression ในเทสความตรงกับ interp; โปรแกรมที่วน allocate 10^8 ครั้งไม่หมดหน่วยความจำ

## เฟส 4 — JIT (4–8 สัปดาห์)  [เป้า 2, 1]

ฐานที่มีแล้ว [เอกสาร]: IR (`ir.py`) + backend x64 (`irx64.py`) + encoder (`x64.py`) ไม่ใช้ libc

ออกแบบ (ข้อเสนอ **[อนุมาน]**):
1. **JIT แบบ "compile-on-first-call" ก่อน** (method JIT ไม่มี tiering): เมื่อรัน `hs prog.hs` → parse → IR → โค้ดเครื่องลง mmap(RWX→RX) → กระโดดเข้า
   - ถ้าเขียนด้วย Python: ใช้ `ctypes`/`mmap` เรียกโค้ดที่สร้าง (พิสูจน์แนวคิดเร็ว แต่ยังต้องมี Python)
   - ถ้า self-host แล้ว: runtime เป็น native, JIT ในตัวเอง (เฟส 5)
2. เก็บ interpreter เป็น tier ล่าง (ตรวจพฤติกรรมอ้างอิงและ fallback เมื่อเจอ feature นอก subset)
3. **เฟสย่อย 4b:** type feedback + specialization (Int/Float/Str fast path, guard + deopt กลับ interp)
   เพราะภาษา dynamic ทั้งหมด; เริ่มจาก inline caching ของ `+ - < ==` และ index
4. cache โค้ดที่คอมไพล์แล้ว (ไฟล์ .hsc ข้างต้นฉบับ) ลดเวลาเริ่ม — ยังเป็น "ไม่ต้องคอมไพล์เองจากมุมผู้ใช้"
5. `hs prog.hs` เป็นคำสั่งเดียว ไม่มี `build` ให้ผู้ใช้เห็น; `build`/`xbuild` คงไว้สำหรับ AOT/ส่งมอบ binary

**เกณฑ์ผ่าน:** `hs prog.hs` เริ่มรันใน <50 ms สำหรับโปรแกรมเล็ก (วัดจริง), ผล stdout/stderr/rc ตรง interp ทุกไบต์
บนคอร์ปัสเดียวกับเฟส 2, bench ≥ `xbuild` ± 10% และดีกว่า CPython ตามเป้าเฟส 1

## เฟส 5 — Self-hosting (ยาว: 2–4 เดือน)  [เป้า 5]

เหตุผล: ตอนนี้ parser/IR/backend/LSP เป็น Python; SPEC §15.35 เรียก IR ว่า "ก้าวแรกของแผน self-hosting"

ลำดับ **[อนุมาน]**:
1. **ให้ภาษาพอสำหรับเขียน compiler:** dict/hash จริง, string builder, file I/O ครบ, error ที่ดี, recursion/stack ลึก,
   ตัวจัดการหน่วยความจำ (เฟส 3.1) — ทำเป็นรายการ "ขาดอะไรจะเขียน lexer ได้" โดยลองเขียนจริง
2. เขียน **lexer + parser ด้วย hs** (ผลต้อง AST เหมือน `interp.parse_program` เทียบ dump ทั้งคอร์ปัส)
3. เขียน **IR builder + verifier ด้วย hs** (เทียบกับ `ir.py` ด้วย IR text dump `hs.py ir`)
4. เขียน **backend x64 + assembler/ELF writer ด้วย hs** (`x64.py`, `x64gen.py`, `irx64.py` ~ 600 KB — ส่วนใหญ่เป็น `x64gen.py`
   ที่ควรถูกแทนด้วย `irx64`; ให้ตัดของเก่าก่อนพอร์ต)
5. **bootstrap:** stage0 = Python ปัจจุบัน → compile stage1 (hs compiler เป็น ELF) → stage1 compile ตัวเอง = stage2;
   **เกณฑ์ผ่าน:** stage1 และ stage2 ให้ไบนารีเหมือนกันทุกไบต์ (fixed point) และผ่านเทสทั้งชุด
6. ลบการพึ่ง Python/gcc/Boehm ออกจากเส้นทางหลัก (`build` ผ่าน gcc เก็บเป็นตัวเลือก)

## เฟส 6 — FFI ที่ใช้งานได้จริง (2–4 สัปดาห์ ขนานกับเฟส 3–5 ได้)  [เป้า 6]

[เอกสาร] ปัจจุบัน: `extern` ผ่าน C ABI, ชนิดพื้นฐาน, ไม่มี struct/callback/variadic, ห้ามใน unsafe/kernel

1. ตรวจสถานะ `extern` บน `xbuild` (SPEC §15.22–15.28 ระบุว่ายังไม่มีที่ v0.6.14–15) แล้วทำให้เท่ากับ native
2. ชนิดข้อมูล: struct by pointer/by value, array, callback (hs function → C function pointer), variadic (`printf`)
3. ตัวโหลด `.so` เองใน x64 โดยไม่พึ่ง libc ถ้าทำได้ (dynamic ELF loader/`dlopen` เขียนเอง) **[อนุมาน — งานใหญ่; ทางเลือก: ลิงก์ static ผ่าน linker เอง]**
4. ตัวสร้าง binding จากไฟล์ header C อัตโนมัติ (`hs.py bind foo.h`)
5. ตัวอย่างและเทสกับ Rust / Zig / C++ ที่ export C ABI (ตามที่ SPEC §11 อ้าง) — เทสจริงในเครื่องมีคอมไพล์เลอร์เหล่านั้น
- **เกณฑ์ผ่าน:** เรียก libc (`printf`, `qsort` พร้อม callback), libm, ไลบรารี C ภายนอกอย่างน้อย 1 ตัว (เช่น sqlite หรือ zlib) และ `.so` ที่ Rust สร้าง จาก hs ได้ในโหมด interp, build, xbuild
- นอกขอบเขต (ตัดแล้ว): CPython C-API / ไลบรารี Python ครบ

## เฟส 7 — OS ให้ครบพอใช้ (ต่อเนื่อง)  [เป้า 4]

ที่มีแล้ว [เอกสาร] ถึง ATA PIO driver (v0.6.17) ที่ไม่มีใน SPEC ที่อ่านและต้องตรวจ [อนุมาน]: network, ดิสก์จริง/filesystem บนดิสก์, SMP, ACPI/APIC, กราฟิก, bootloader เอง, รันบนเครื่องจริง

ลำดับข้อเสนอ: (1) filesystem บนดิสก์ (ext2-like หรือแบบง่าย) เหนือ ATA (2) ELF loader ใน kernel รันโปรแกรม user
ที่เขียนด้วย hs (3) bootloader/UEFI เองหรือ multiboot ที่ไม่ต้องพึ่ง QEMU `-kernel` (4) network (virtio-net หรือ e1000 + ARP/IP/UDP/TCP แบบเล็ก)
(5) APIC/timer ใหม่/SMP (6) boot บนเครื่องจริง/VM อื่น
**เกณฑ์ผ่านต่อข้อ:** เทส QEMU อัตโนมัติ (ต่อยอด `test_xkernel.py`) + demo สั้น

## เฟส 8 — AI-first: วัดและเสริม (ทำคู่ไปกับทุกเฟสเริ่มตั้งแต่เฟส 1)  [เป้า 7, 3]

ฐาน [เอกสาร]: AGENTS.md, for-agents.md, api.json, errors.md, error `--json`, LSP, docs ที่เทสตรวจ

1. **eval suite:** 50–100 โจทย์เขียนโปรแกรม (`evals/*.md` + เทสอัตโนมัติ); รันกับโมเดลหลายตัวในโหมด "มีเอกสาร" และ "ไม่มีเอกสาร"; ตัวชี้วัด: pass@1, จำนวนรอบแก้, token ต่อโปรแกรม; เทียบ Python บนโจทย์เดียวกัน
2. ทุก error มีรหัส + คำแนะนำแก้ (`E0xx: …; hint: …`) เป็น JSON (ต่อยอด errors.md)
3. `hs fmt` canonical ที่ไม่ตัดคอมเมนต์ (ทำแล้ว: `fmt -w` เก็บคอมเมนต์ (ตำแหน่งอาจขยับ blank line ยังหาย)) — AI เขียนคอมเมนต์ได้โดยไม่หาย
4. คำสั่ง "agent mode": `hs check --json`, `hs explain <error>`, `hs test` ที่ส่งผลเป็น JSON; LSP ที่ใช้ได้ผ่าน MCP/CLI
5. ตัดความกำกวมของภาษา (มีทางเขียนเดียว), ลบ divergence ที่ต้องจำ (เช่น `/` ใน unsafe ต่างจาก safe)
6. ชุดตัวอย่าง "โจทย์→โค้ด" ที่รันได้ ให้โมเดลเรียนจากบริบท
- **เกณฑ์ผ่าน:** รายงานผล eval ทุกรุ่น; เป้า **[อนุมาน]** pass@1 ≥ 80% ของ Python บนโจทย์ชุดเดียวกัน เมื่อให้ AGENTS.md เป็นบริบท

## ลำดับสรุป

```
เฟส 0 (CI/ฐาน) → เฟส 1 (bench+eval เริ่ม) → เฟส 2 (kernel→IR)
      → เฟส 3 (ภาษา+optimizer) → เฟส 4 (JIT) → เฟส 5 (self-host)
      ขนาน: เฟส 6 (FFI), เฟส 7 (OS), เฟส 8 (AI eval) ตลอดทาง
```

## ความเสี่ยงและข้อสังเกตตรง ๆ

1. **ขอบเขตใหญ่มากสำหรับคนเดียว/AI ช่วย** (ภาษา + 4 backend + JIT + OS + self-host + FFI) — แนะนำจบเฟส 0–2 ก่อน
   และกำหนดว่าเป้า "เร็วกว่า Python" วัดที่งานไหนบ้างตั้งแต่เฟส 1
2. **JIT บนภาษา dynamic ทั้งหมดยาก** ถ้าไม่มี type feedback จะเร็วแค่ระดับ "baseline" — ยอมรับได้ถ้าเป้าคือเร็วกว่า CPython ไม่ใช่เท่า V8/LuaJIT
3. **"พึ่งตัวเองสมบูรณ์" ขัดกับ "เข้ากันได้กับทุกภาษา":** FFI ผ่าน C ABI ต้องมี dynamic loader — ถ้าไม่ใช้ libc ต้องเขียนเอง
4. **ความตรงทุกไบต์กับ interp** คือจุดแข็งของโปรเจกต์นี้ (differential testing) แต่ทำให้การเปลี่ยน semantics (เช่น Int 64-bit) ต้องเปลี่ยน interp ก่อน
5. **เทสเดิมมองไม่เห็นบั๊ก** (v0.6.30 เจอ 5 ข้อ) → เพิ่ม fuzz/differential เป็นหลักทุกเฟส ไม่ใช่แค่เทสเคสเขียนมือ
6. **ภาษาใหม่ + AI-first:** โมเดลไม่เคยเห็น hs ในข้อมูลฝึก คุณภาพขึ้นกับเอกสาร/ตัวอย่าง/error ล้วน ๆ จึงต้องวัด (เฟส 8) ไม่ใช่เดา
7. **ข้อจำกัดความเข้าใจของผู้เขียนแผนนี้:** อ่าน SPEC, README, docs/index.md, commit log และหัวข้อของแผน IR แต่ไม่ได้รันเทสหรือ benchmark
   ตัวเลขเวลาทั้งหมดมาจาก SPEC ไม่ได้วัดซ้ำ

## สมมติฐานที่ต้องยืนยัน

- เป้าหมายความเร็ว (กี่เท่าของ CPython, ในงานแบบไหน) — เจ้าของยังไม่ได้ระบุตัวเลข
- license ที่ต้องการ
- ต้องการให้ OS รันบนเครื่องจริงหรือแค่ QEMU
- ยอมให้ Python เป็น stage0 ของ bootstrap ถาวร (แค่ครั้งแรก) หรือไม่
- ลำดับความสำคัญระหว่างเฟส 4 (JIT) กับเฟส 5 (self-host) กับเฟส 7 (OS)

## B-path compiler port checkpoints (2026-10-14)

- S1: `asm.hs` + `elf.hs` emit the same static ELF bytes as Python.
- S2: `irlib.hs` reads the existing textual IR interchange.
- S3: `gcrt.hs` and `be/be.hs` emit byte-identical hosted images on the
  single-file differential corpus. Module source lowering, dynamic ELF/FFI,
  and a full compiler fixed point are not yet proved.
- S5a: `be/irbuild.hs` lowers the canonical parser AST to the unoptimized
  flat CFG used by `ir.py`. `_n`/`_t` records, block/temp numbering, functions,
  unsafe operations, closures and finally inlining must match structurally.
  `test_irbuild.py` feeds the same canonical AST JSON to Python and hs,
  validates each result with the Python verifier, and compares the whole
  module. The hs builder is tested through interp and a compiled x64 driver;
  ASTs containing integers outside the x64 62-bit payload are explicitly
  interp-only. Parser normalization (defaults/range/prelude), the optimizer,
  the self-hosted verifier, module loading and bootstrap are separate gates.
  This checkpoint does not claim a Python-free compiler.

S5b optimizer checkpoint: `be/iropt.hs` folds and removes unused constants
with whole-module structural equality to `iropt.py`, through interp and x64.
A separate seeded boundary matrix checks arithmetic folding near the 62-bit
limits. Multiplication is bounded before it can wrap into a false constant.
This stage still consumes canonical IR JSON; parser normalization and the
full compiler driver are not part of this checkpoint.
S5 verifier checkpoint: `be/verify.hs` checks CFG labels, terminators,
SSA definitions, dominance, phi predecessors and instruction uses. Valid
corpus modules and deliberately malformed modules are checked against the
Python verifier, through interp and x64. Out-of-width IR constants remain
interp-only. This is a compiler-stage check, not a full bootstrap claim.
Compiler-depth regression gate: repeated returns from an except handler
must pop the active exception value, not the already-consumed try frame.
`tests/t_exceptreturn.hs` exercises 300 handled returns with and without
finally. The Python IR builder and its hs translation share this cleanup
rule; interp remains the output oracle.

Native hosted-compiler checkpoint: `selfhost/be/compile_hex.hs` builds through
Python stage0, then the resulting native compiler builds itself. The test
requires stage1 == stage2 == stage3 byte for byte. Output is chunked hex to
bound memory; this driver is not a polished CLI. `test_native_compiler.py`
also compares hosted ELF output against Python across the source corpus.
One full-width unsafe-constant program remains explicitly deferred. A
successful hosted fixed point does not cover the separate kernel backend,
all 64-bit unsafe values, or the missing x64 write_bytes helper. No binary
seed is yet committed. The Python source remains the reference/test oracle.

The x64 IR path now supports direct `write_bytes(path, [Int 0..255])`.
Validation runs before opening the file; empty data and embedded zero bytes
are preserved. `test_write_bytes_x64.py` compares exact file bytes and
catchable failures with interp, including invalid elements and non-list
inputs. First-class write_bytes values remain outside the x64 subset.

Source-to-ELF driver checkpoint: `selfhost/be/compile.hs SOURCE OUTPUT`
connects normalized parsing, optimized IR, verification, module loading,
JSON helper compilation and static/dynamic ELF emission. Its interp-run
image must equal the Python backend byte for byte, including module and
FFI programs. This is not yet a Python-free bootstrap: compiling this
compiler to x64 and reaching a fixed point remain separate gates.

S5c parser normalization: `be/normalize.hs` applies default-argument filling,
range-step lowering and prelude injection after `parselib.parse`. Prelude
source is copied from the reference as data by `scripts/mkprelude.py`.
`test_normalize.py` compares the full normalized AST; `test_pipeline.py`
compares source -> optimized CFG through interp and compiled x64. The
13k-line backend emitter is explicitly deferred to a separate slow bootstrap
gate, and out-of-width ASTs are interp-only. Modules are lowered individually
here; linking their imports belongs to the compiler-driver stage.
S5 verifier checkpoint: `be/verify.hs` checks CFG labels, terminators,
SSA definitions, dominance, phi predecessors and instruction uses. Valid
corpus modules and deliberately malformed modules are checked against the
Python verifier, through interp and x64. Out-of-width IR constants remain
interp-only. This is a compiler-stage check, not a full bootstrap claim.

Measured binary-driver fixed point: scripts/bootstrap-hosted.sh produced
three identical 9,080,008-byte ELF compilers locally. Stages two and three
were built by the native compiler with no Python process in those steps.
The seed is not committed and full CI remains the merge gate.
