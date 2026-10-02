# holyshit — SPEC v1.0 (ภาษาใหม่: dynamic + indent + ปลายทาง native)

> สถานะ: สเปกภาษาระดับ design (เฟส 1) ยังไม่ลงโค้ด
> หลักการ: เขียนง่ายกว่า Python, รันทันทีแบบ JIT workflow, แกน dynamic เต็มตัว,
> งาน low-level อยู่ใน `unsafe` เท่านั้น, syntax พังจาก v0.3 ได้ (v0.3 เก็บไว้เป็น legacy)

## 1. Lexical

- ย่อหน้า (indent) มีความหมายแบบ Python: block เริ่มหลังบรรทัดที่ลงท้าย `:`
- indent ต้องสม่ำเสมอใน block เดียวกัน (แนะนำ 2 หรือ 4 ช่อง, ห้าม tab นำหน้า)
- ไฟล์สคริปต์ใช้นามสกุล `.hs`, รันด้วย `python3 interp.py prog.hs`
- block (if/while/for) ไม่สร้าง scope ใหม่ — มีแค่ function เท่านั้นที่สร้าง scope (แบบ Python)
- จบ statement ด้วยขึ้นบรรทัดใหม่ (`;` ใช้ไม่ได้แล้ว)
- คอมเมนต์: `#` และ `//` ถึงท้ายบรรทัด
- string: `"..."` มี escape `\n \t \" \\`, ไม่มี string หลายบรรทัดใน v1

## 2. ค่า (dynamic ทั้งหมด, ไม่มีประกาศ type)

| ชนิด | ตัวอย่าง | หมายเหตุ |
|---|---|---|
| Int | `42`, `-7`, `0xFF` | 64-bit signed |
| Float | `3.14`, `2.0` | 64-bit |
| Str | `"hello"` | UTF-8, ต่อด้วย `+` ได้ |
| Bool | `true`, `false` | |
| Null | `null` | ค่าเริ่มต้นของ var ที่ยังไม่ assign ไม่ได้ — ต้อง assign ก่อนใช้เสมอ |
| List | `[1, 2, "x"]` | เก็บค่าผสมชนิดได้, `a[i]`, `a[i] = v` |
| Dict | `{"k": 1}` | key เป็น Str เท่านั้นใน v1 |
| Func | `def` สร้าง | first-class: ส่งเป็น arg / คืนจาก func ได้ |

- `+` ใช้ได้กับ Int+Int, Float+Float (ผสม Int+Float ได้ → เป็น Float), Str+Str (ต่อ string)
- `- * / %` ใช้กับตัวเลข (`/` หารทศนิยมเสมอ ได้ Float, หารด้วย 0 = error)
- `//` ไม่มีในฐานะ operator — `//` เริ่มคอมเมนต์ทั้งบรรทัด (เหมือน `#`)
- `pass` = คำสั่งว่าง (ไว้เติม block ที่ยังไม่เขียน)
- เปรียบเทียบ: `== != < > <= >=` ใช้กับชนิดเดียวกัน (Str เทียบ lexicographic ได้)
- ตรรกะ: `and or not` (short-circuit), truthiness: `false null 0 "" [] {}` เป็นเท็จ ที่เหลือจริง
- ผิดชนิดตอนรัน (เช่น `1 + "a"`) = runtime error พร้อมบรรทัดที่ผิด

## 3. ตัวแปรและฟังก์ชัน

```
x = 10            # สร้าง/แก้ var, ไม่ต้องประกาศ
x = x + 1

def fib(n):       # def name(params):
  if n < 2:       # block ด้วย indent
    return n
  return fib(n - 1) + fib(n - 2)

print fib(10)     # เรียกแบบมีวงเล็บ; เรียก 0 arg วงเล็บได้หรือละก็ได้
```

- `return expr` / `return` (ได้ Null)
- ขอบเขต: local ใน func, global นอก func; func อ่าน global ได้, เขียน global ต้อง `global x` ก่อน (แบบ Python)
- recursion ได้, closure ได้ (snapshot ค่าตอน `def` — copy semantics;
  interp แชร์ env อยู่, native ก็อป; self-recursion ได้, mutual recursion ระหว่าง
  nested func ยังไม่ได้, kernel ห้าม closure ให้ใช้ global)

## 4. ควบคุมโฟลว์

```
if x > 0:
  print "pos"
elif x < 0:
  print "neg"
else:
  print "zero"

while n > 0:
  n = n - 1

for i in range(5):       # 0..4
  print i
for x in [10, 20]:
  print x
for k in {"a": 1}:       # วน key
  print k
```

- `break` / `continue` ใน while/for
- `range(n)` = 0..n-1, `range(a, b)` = a..b-1 (ของเก่า `0..5` ตัดออก ใช้ range แทน)

## 5. Builtins ชุดแรก (v1)

- `print a, b, ...` → คั่นช่องว่าง + ขึ้นบรรทัดใหม่ (เหมือน v0.3), `print` ว่างๆ = บรรทัดเปล่า
- `len(x)` → ความยาว Str/List/Dict
- `range(n)`, `range(a, b)`
- `str(x)`, `int(x)`, `float(x)` แปลงชนิด (แปลงไม่ได้ = error)
- `input()` อ่าน 1 บรรทัดจาก stdin → Str
- File (น้อยสุดที่พอใช้): `open(path, mode)` + `read(f)` + `write(f, s)` + `close(f)` โดย mode `"r"`/`"w"`
- `len` ใช้กับ Dict = จำนวน key
- String/List: `append(a, x)`, `split(s)` / `split(s, sep)`, `find(s, sub)` (-1 ถ้าไม่เจอ),
  `join(sep, list)`, slice `s[a:b]` / `s[:b]` / `s[a:]` (list ก็ได้, index ติดลบได้)
- Process: `argv()` → List ของ args (ไม่รวมชื่อโปรแกรม), `env(name)` → Str/Null,
  `system(cmd)` → Int exit status (ผ่าน shell)
- Net (http อย่างเดียว, ไม่มี https): `tcp_connect(host, port)` + `tcp_send/recv/close`,
  `tcp_listen(port)` + `tcp_accept`, `http_get(url)` → body ของ 2xx (อื่น error)
- JSON: `json_parse(s)` ↔ `json_str(x)` (ลึกเกิน 200 ชั้น = error)
- Agent kit: `read_text/write_text/append_text` (ไฟล์ทั้งก้อน), `exists/ls/mkdir`,
  `json_load/json_save` (ไฟล์ JSON ตรง), error ทุกตัวมี `--json` โหมดให้ agent parse
- ทั้งหมดนี้ใช้ใน kernel ไม่ได้ (ban ชัดเจน) ยกเว้น `ticks/readkey/pmm_alloc/meminfo`
  ที่มี approximation ฝั่ง kernel

## 5.1 Module และ stdlib

- `import mod` / `import pkg.mod` (dotted แปลงเป็น path, หาใน dir โปรแกรมก่อน,
  แล้ว `HSPATH` (คั่นด้วย `:`), แล้ว cwd)
- parent ที่ไม่มีไฟล์เป็น package เปล่าอัตโนมัติ, init ครั้งเดียว, circular = runtime error
- ใช้ attr ข้ามได้ทุกระดับ (`std.str.trim(...)`), `import` ซ้ำโมดูลเดิมได้
- `std/` มากับภาษา: `std.str` (trim/pad/starts_with/ends_with/lines),
  `std.list` (map/filter/fold/any/all), `std.heap` (heap_init/malloc/free,
  heap_free/heap_nblocks — free-list allocator เขียนด้วย hs+struct เอง)

## 6. Error

- `try:` / [`except:` [`as e`]] / [`finally:`] (ต้องมี except หรือ finally อย่างน้อยหนึ่ง)
  `e` เป็น string `"msg at line N"`, รองรับ nested try + `break/continue/return` ข้างใน
  (native ใช้ setjmp/longjmp, C locals เป็น volatile เฉพาะ func ที่มี try)
  `finally` รันทุกทางออกทั้งสอง backend (รวม return/break/continue และ error ที่ propagate)
- `raise "msg"` โยน error เอง (ต้องเป็น Str), `raise` ลอยๆ = re-throw ใน `except`
  (native ใช้ lexical frame — ข้ามขอบ function ไม่ได้, interp ได้)
- error ที่ไม่มี try ดัก หยุดโปรแกรมทันที พิมพ์ `error: <สาเหตุ> at line N`

## 7. `unsafe` (static subset สำหรับงาน low-level — ทำแล้ว เฟส 4a)

block `unsafe:` ข้างในเป็นภาษา static อีกภาษาหนึ่ง กฎต่างจากแกน dynamic:

- **ชนิดมี 3 ตัว**: `I64` (signed 64), `U64` (unsigned 64), `Ptr` (pointer ไบต์)
  บวก struct pointer `Name*` (ดูข้างล่าง)
- **ห้าม**: float, string, list, dict, `def`, `for`, เรียกฟังก์ชัน dynamic
  (`print` ใช้ได้, string literal ใช้กับ `print` ได้อย่างเดียว)
- **หน่วยความจำ**: `Ptr p = alloc(n)` ได้หน่วยความจำ zeroed n ไบต์ (GC เก็บให้ ไม่ต้อง free)
  `*p` / `*p = v` อ่าน/เขียน 64-bit (ต้อง align 8, ไม่งั้น error),
  `load8/load32/store8/store32` เข้าถึงกี่ไบต์ก็ได้
- **pointer**: `p + n` / `p - n` ขยับเป็นไบต์, `p - q` ระยะห่าง, `==`/`!=` ได้ ห้าม `< >`
  `as_ptr(int)` แปลงเลขเป็น address (ไว้ทำ MMIO เช่น `as_ptr(753664)`),
  `as_int(p)` แปลงกลับ, `null` คือ address 0
  (ทุกตัวนี้รับ struct pointer ได้ — struct สลายเป็น address เสมอ)
- **struct** (layout hardware/driver โดยตรง):
  ```
  unsafe:
    struct Desc:
      U64 low
      U64 high
      U64 entries[512]
      Node* next        # ชี้ struct อื่น (ต้องประกาศก่อน) / self-ref ได้
    Desc* d = alloc(sizeof(Desc))   # sizeof ได้ทั้ง struct และ I64/U64/Ptr (=8)
    d.low = 4660
    d.entries[3] = 22
    print d.low
  ```
  - field มีแต่ `I64/U64/Ptr/Struct*` (+ array `[N]` คงที่), ทุก field 8 ไบต์ ไม่มี padding
  - `p + n` / `p - n` ขยับทีละ `sizeof` (C semantics), `p - q` (struct เดียวกัน) = จำนวนตัว
  - `p.field` / `p.arr[i]` อ่าน, `p.field = v` เขียน — มี bounds check + null check
    ฝั่ง native เป็น volatile access ทั้งหมด (MMIO ปลอดภัย)
  - `as_int(p)` / `load/store*` รับ struct pointer ได้เลย
  - struct เป็นชื่อระดับโปรแกรม (ประกาศซ้ำ layout เดิมได้, ต่าง = error),
    ผูกกับ build เดียว (ไม่ข้ามไฟล์ test/run ใน process เดียวกัน)
  - ยังไม่มี: nested struct แบบค่า (มีแต่ pointer), bitfield, union, `->` (ใช้ `.` แทน)
- block ซ้อนใน `unsafe:` (`if`/`while` ข้างใน) ใช้กฎ static เหมือนเดิม
  ทั้ง parse และ runtime (ไม่มี dynamic หลุดเข้าไป)
- เขียน global จากใน func ต้อง `global` (กฎเดียวกับ Python ใช้กับ unsafe ด้วย)
- **strict**: ห้ามผสม `I64` กับ `U64` (error ทั้งสอง backend ข้อความเดียวกัน),
  literal เลขปรับตามบริบท, `/` และ `%` ตัดทศนิยมทิ้งแบบ C (ต่างจาก `/` ของ safe ที่ได้ Float)
- **`and/or/not` ใน unsafe คืน I64 0/1** (ไม่คืน operand แบบ safe)
- **`asm("...")`**: ส่ง assembly ตรงลง binary (ใช้ได้เฉพาะ `hs.py build`, interpreter ตอบ error ชัดเจน)
- **ทุก load/store เป็น volatile** ใน C ที่ generate — เขียน MMIO ปลอดภัย
- **สะพาน dynamic**: อ่าน var dynamic ใน unsafe = unbox เป็น I64 พร้อมเช็คชนิด (ผิดชนิด error),
  เขียนค่าออกไปนอก unsafe = box อัตโนมัติ (`U64` เกิน 63 bit ตอน box จะ error)
- **scope**: var unsafe อยู่ใน function (หรือ global ถ้าอยู่นอก func), zero-init,
  ห้าม capture ข้าม function (compile error), ห้าม `global` กับ var unsafe
- ชื่อสงวนเพิ่มเติม (ห้ามตั้งเป็น var/func): `import module try except`

ตัวอย่าง (แตะ “hardware” จำลอง):
```
unsafe:
  Ptr uart = as_ptr(1016)   # จริงๆ คือ MMIO address
  store8(uart, 72)          # เขียนไบต์เดียว
  print load8(uart)         # อ่านกลับ
```

ที่ยังไม่มี (ต้อง freestanding runtime + boot ก่อนถึงจะเป็น kernel จริง):
รันบน bare metal ไม่ได้ — binary ตอนนี้ยังพึ่ง libc/GC ของ OS อยู่

## 8. โปรแกรมตัวอย่าง (ต้องรันได้หลังเฟส 2)

```
# fib + file
def fib(n):
  if n < 2:
    return n
  return fib(n - 1) + fib(n - 2)

print "fib:", fib(10)

f = open("out.txt", "w")
write(f, str(fib(15)))
close(f)
```

## 9. โน้ตสำหรับคนทำ interpreter (เฟส 2)

- value = tagged union ใน Python (dict/tuple) ไปก่อน, ไม่ต้องคิดเรื่อง performance
- เริ่มจาก tree-walk ตรงๆ บน AST; ห้าม optimize ใดๆ ในเฟส 2
- ชุดเทสขั้นต่ำ: fib recursive, while sum, for+range, list/dict, file write/read กลับ, error ผิดชนิดต้องมีเลขบรรทัด

## 10. Backend native (เฟส 3 — ทำแล้ว 3a, เหลือ 3b)

- 3a (เสร็จ, `hs.py` + `native/rt.{h,c}`): AST จาก `interp.py` → C → `gcc -O2 -lgc` เป็น native binary
  (`hs.py build prog.hs [-o prog]`, `hs.py run prog.hs` = build ลง temp แล้วรันทันที)
- value = tagged `Val` (16 bytes), หน่วยความจำใช้ Boehm GC — ไม่มี refcount bookkeeping
- fib(22): interpreter 0.85s → native 0.009s (~95x), binary 35KB
- ข้อจำกัดที่ปลดแล้ว: closure ใช้ได้ (copy semantics ผ่าน `v_func_setcaps` + `hs_cur_caps`),
  เหลือแค่ mutual recursion ระหว่าง nested func (ใช้ global แทน)
- เครื่องมือ: `hs.py check` (parse+scope ไม่ต้องมี gcc), `--version`, `run` ส่ง args ต่อ,
  `VERSION` + `.gitignore` + `README.md` + `legacy/` (ของ v0.3)
- 3b (เสร็จ): `import` ระบบ module (init ครั้งเดียว, circular = runtime error),
  `m.attr`/`m.attr=` (static ตรง + dynamic ผ่าน registry), `v_slice`, builtins
  `append/split/find/join`, `try/except[as]` (setjmp, volatile เฉพาะ func ที่มี try)
- `tests/test_native.py`: **17/17 ผ่าน** ตรงกับ interpreter ทุกตัวอักษรรวม error + เลขบรรทัด
  (`mod_*` เป็น helper ไม่ build ตรง, `uasm` native-only)
- เหลือ: `for` แบบไม่ materialize seq, dict แบบ hash จริง (ของเดิม)

## 11. `extern` — ใช้ของจากภาษาอื่น (C ABI = ตัวกลางสากล)

```
extern:                       # libc (default)
  I64 puts(Str s)
  U64 strlen(Str s)
  Ptr malloc(U64 n)
  U0 free(Ptr p)

extern from "m":              # -lm (ชื่อล้วน = -l, มี / = path, .c = คอมไพล์+ลิงก์ให้)
  F64 sin(F64 x)

extern from "helper.c":       # ซอร์ส C (เช่น ส่วน kernel ที่เขียนด้วย C) — build ให้เอง
  I64 hs_add3(I64 a, I64 b, I64 c)
```

- ชนิดที่ขอบ: `U0` (void, เป็น return ได้อย่างเดียว), `I64 U64 F64 Str Ptr`
  `Str` = `char*` (NUL-terminated), `Ptr` = address เป็น Int ฝั่ง dynamic
- เรียกได้จาก safe code เท่านั้น (ห้ามใน `unsafe`, ห้ามใน kernel — kernel ไม่มี libc)
- native ไม่ emit prototype แต่ `dlsym` ตรง (`-rdynamic -ldl`) เลยไม่ชนชื่อฟังก์ชัน libc
- interp รันผ่าน `ctypes` (รวม `.c` ที่คอมไพล์เป็น .so ชั่วคราวให้) ผลตรง native ทุกตัวอักษร
- ทำไม่ได้: struct, callback, variadic (เช่น `printf` ตรงๆ) — เขียน wrapper C ครอบเอา
- ต่างภาษา = ต่างแค่ต้นทาง: Rust/Zig/C++/Go(cgo) ที่ export C ABI เอา `.so`/`.a`/`.o`
  มา `from` ได้หมด; ซอร์ส C ของ kernel เอามาลิงก์ตรงได้แบบ `helper.c` ข้างบน

## 12. Kernel (xkernel freestanding ล้วน — สาย gcc ถูกลบออกแล้ว)

- ประวัติ: เฟส 5a ใช้ gcc/as/ld + krt.c (C runtime) — ถูกลบทั้งหมดเมื่อ xkernel
  ครอบคลุมพฤติกรรมครบ (ดู git history) ตอนนี้ kernel มาจาก `.hs` + encoder ล้วน
- `kernel/` เหลือแต่ `.hs` (xdemo/kx2/kxexc_*); `tests/test_xkernel.py` **18/18**
  (boot, fib, timer ~200 ticks, keyboard, PMM 32768/-3, EXC 14/0)
- runtime kernel = hs subset + asm ใน `x64gen.py` (serial, bump heap, IDT/PIC/PIT,
  ticks/readkey/pmm) — ไม่มี C เหลือในสาย kernel เลย

## 13. Backend x86-64 ตรง (เฟส 6a — hosted subset, ไม่ใช้ gcc/as/ld/libc)

- `x64.py`: assembler + static ELF64 writer เขียนเอง (REX/ModRM/SIB, rel32/rip-rel,
  2 segments RX+RW, entry `_start`)
- `x64gen.py`: hs subset → machine code; runtime ใน asm (`print_int`, `x_alloc` ผ่าน
  mmap, `divzero`, `_start`+exit) — binary 4KB ไม่พึ่ง libc เลย
- subset: Int, Str literal (print อย่างเดียว), def/call/recursion/closure (caps ผ่าน r15),
  if/while, unsafe I64/U64/Ptr + struct, `print`/`int()`; `/` ตัดทศนิยมแบบ C
- runtime: bump allocator บน mmap arena 16MB (align 16, ไม่ free — แบบ kernel heap),
  ขยาย arena อัตโนมัติเมื่อเต็ม, `alloc` ใหญ่กว่า 16MB ได้ arena ของตัวเอง
- วัดจริงบน i7-6700HQ (TSC 2592MHz): fib(25) 0.003s (gcc-Val 0.021s, interp 3.79s),
  binary 4KB เทียบ 77KB; timer-IRQ latency (SIGALRM, `scripts/irq_lat.py`):
  @2ms med 2000us p99 +100us max +116us, @500us p99 +37us max +70us
  (เลขนี้คือ Linux shared laptop ไม่ใช่ bare metal — bare metal ควรอยู่ระดับ ~1-5us)
- ยังไม่มี: Float/List/Dict, import, try, extern, string ops, argv, slice/attr,
  `for`, `asm()` (ใช้ไม่ได้กับ encoder ของตัวเอง) — เป็น compile error ชัดเจน
- `hs.py xbuild prog.hs [-o prog]` / `hs.py xrun prog.hs`, เทส `tests/test_x64.py`

## 14. Kernel freestanding ด้วย x64 backend ล้วน (เฟส 6b — ไม่ใช้ gcc/as/ld)

- `hs.py xkernel prog.hs -o k.elf`: encoder 32-bit (`Asm32`) + trampoline
  (cli → cr3/cr4/EFER/cr0 → lgdt → far jmp) + page table prefill ใน Python
  (identity 1GB) + payload 64-bit + ELF32 writer — ผลลัพธ์บูต QEMU ได้จริง
- freestanding runtime: serial COM1, bump heap คงที่ 16MB ที่ 32MB, halt;
  `print`/unsafe/alloc/struct ครบ, float/list/dict/import/try/extern ไม่มี
- `kernel/xdemo.hs` + `tests/test_xkernel.py`: **6/6 ผ่าน** (serial: boot, fib 55,
  sum 45, alloc readback 7, halted)
- เหลือ: IDT/PIC/timer/keyboard/paging แบบไดนามิก, scheduler, filesystem
