# holyshit — SPEC v1.0 (ภาษาใหม่: dynamic + indent + ปลายทาง native)

> สถานะ: v0.6.10 — ภาษา + 4 backend (interp / native gcc / x86-64 ตรง /
> kernel freestanding) + stdlib + formatter + language server + เอกสารที่เทสตรวจ
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
- Memory: `read_mem(ptr, nbytes)` → Str ของ `nbytes` ไบต์ดิบที่ address `ptr`
  (byte-preserving: NUL กับไบต์สูงรอด, ต่างจาก UTF-8 decode) — ต้องการอ่าน
  โครงสร้างที่ allocator ไม่ได้เป็นเจ้าของ (boot info, ramdisk) และเป็นตัวเดียวที่
  ทำงานได้ครบทุก backend รวมถึง kernel
- ทั้งหมดนี้ใช้ใน kernel ไม่ได้ (ban ชัดเจน) ยกเว้น `ticks/readkey/pmm_alloc/meminfo`
  ที่มี approximation ฝั่ง kernel และ `read_mem` ที่ใช้จริง

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
- `x64gen.py`: hs subset → machine code; runtime เขียนเป็น machine code ล้วน
  (print_int/fmt_int, bump malloc ผ่าน mmap, type_err, divzero, `_start`+exit) —
  ทั้งหมดประกอบด้วย instruction ที่ encoder เขียนเอง
- **ค่าแบบ tagged (v2)**: low 2 bits = tag — `01` Int (payload 62-bit, `v<<2|1`),
  `10` Bool (0x02 false / 0x0A true), `11` Null 0x03 / Unbound 0x0B, `00` heap object
  (`[kind][len][bytes]` = Str, `[kind][code][caps…]` = Func,
  `[kind][len][cap][buf]` = List) → Str/Bool/Null/List เป็นค่าเต็ม
  ไม่ใช่แค่ int; `print` เลือกเองจาก tag, type error = `type error` + exit(1)/halt
- runtime ฝั่งค่า: `x_str_at` (สร้าง Str จาก rodata), `x_str_cat`, `x_str_cmp`
  (ใช้ทั้ง `==`/`!=` และ `<`/`>`), `x_str` (รวม List → `[1, x]` ผ่าน `x_list_str`),
  `x_num_to_str`, `x_len` (Str/List), `x_truth`, `print_val` (+ `x_print_list`
  พิมพ์ `[a, b]` ซ้อนกันได้), `x_eq` (+ `x_list_eq` เทียบลึก), `x_cmp`,
  `x_slice`, `x_split1/2`, `x_find`, `x_join` และตาราง whitespace 256-byte —
  ทั้งหมดประกอบด้วย instruction ที่ encoder เขียนเอง
- subset: Int, Str (literal เป็นค่าได้, `+` ต่อสาย, `len`, เทียบซ้ำกันได้,
  slicing `s[a:b]` แบบ byte, `split`/`find`/`join`),
  List (`[..]`, `+` ต่อกัน, `len`, `append` (header อยู่กับที่ เติบโตแค่ buf —
  alias เห็นตรงกัน), `==` เทียบลึก, `l[i]`/`l[-1]`/`l[i] = v`, `range()` คืน List
  จริง, `for x in <list>`), Bool, null, not/and/or (คืน operand ตาม hs),
  if/elif/else, while, `for` (`for i in range([a,] b)` lower เป็น counter loop;
  `for c in <str>` ได้ Str ทีละตัวอักษร), break/continue (ใช้ได้ทั้ง while/for
  ซ้อนกัน), def/call/recursion/closure (caps ผ่าน r15),
  `import` (ไฟล์จริงหรือ dotted package; body รันครั้งเดียวผ่าน guarded init
  parent-first; อ่าน/เขียน `mod.attr`, `print mod` → `<module name>`;
  หาไฟล์จาก program-dir + HSPATH; circular = compile error),
  `global` (ฟังก์ชันแก้ global ของโมดูลตัวเองได้), `str()` (รวม List),
  `int()`/`len()`, `print` (List ซ้อนกันได้), unsafe I64/U64/Ptr + struct;
  `/` ตัดทศนิยมแบบ C; index เกินขอบ = `index out of range`;
  โมดูลเป็น compile-time only (ส่งโมดูลเป็น value ไม่ได้ — ใช้ `mod.attr`)
- exceptions แบบเต็ม (`try`/`except`/`finally`/`raise`): setjmp/longjmp เขียนเอง
  บน handler stack คงที่ 256 เฟรม (ไม่ใช้ libc), error ทุกจุดมี message + line
  ตรง interp (`cannot add Int and Str`, `unknown variable 'x'`, `not callable`,
  `len of`, `not iterable` ฯลฯ ผ่าน `x_tname` + ตัวสร้าง string);
  `except as e` ผูก `"msg at line N"`, bare `raise` re-raise แบบ lexical;
  `break`/`continue`/`return` ใน try รัน finally + pop handler ถูกต้อง;
  uncaught พิมพ์ `error: msg at line N` exit 1; reads ที่ไม่เคย assign เป็น
  UNBOUND แล้ว error ตอนอ่าน (ไม่ใช่ขยะจาก stack)
- runtime: bump allocator บน mmap arena 16MB (align 16, ไม่ free — แบบ kernel heap),
  ขยาย arena อัตโนมัติเมื่อเต็ม, `alloc` ใหญ่กว่า 16MB ได้ arena ของตัวเอง
- วัดจริงบน i7-6700HQ (TSC 2592MHz): fib(25) ~0.007-0.012s (gcc-Val 0.021s, interp 3.79s),
  (เคย 0.005s ก่อนใส่ error-check + unbound-check ทุกจุด — จ่ายค่า diagnostics),
  binary 4KB เทียบ 77KB; timer-IRQ latency (SIGALRM, `scripts/irq_lat.py`):
  @2ms med 2000us p99 +100us max +116us, @500us p99 +37us max +70us
  (เลขนี้คือ Linux shared laptop ไม่ใช่ bare metal — bare metal ควรอยู่ระดับ ~1-5us)
  (fib เพิ่มจาก 0.003s เป็น 0.005s หลังเพิ่ม tag arithmetic — จ่ายค่า representation)
- ยังไม่มี: Float/Dict, extern, attr บนค่า (มี attr ได้เฉพาะโมดูล),
  argv, `split`/`find`/`join`, `asm()` (ใช้ไม่ได้กับ encoder ของตัวเอง) —
  เป็น compile error ชัดเจน
- ใน `unsafe:` ค่ายังเป็น machine word ดิบ (literal ไม่ถูก tag) — ใช้ `as_ptr(x)` /
  `as_int(x)` เป็นสะพานจากค่า dynamic
- `hs.py xbuild prog.hs [-o prog]` / `hs.py xrun prog.hs`, เทส `tests/test_x64.py`
  (**25/25**: + slice, textops, err_slice_idx/obj, err_split/join;
  `mod_*` = helper ไม่รันตรง)

## 14. Kernel freestanding ด้วย x64 backend ล้วน (เฟส 6b — ไม่ใช้ gcc/as/ld)

- `hs.py xkernel prog.hs -o k.elf`: encoder 32-bit (`Asm32`) + trampoline
  (cli → cr3/cr4/EFER/cr0 → lgdt → far jmp) + page table prefill ใน Python
  (identity 1GB) + payload 64-bit + ELF32 writer — ผลลัพธ์บูต QEMU ได้จริง
- freestanding runtime: serial COM1, bump heap คงที่ 16MB ที่ 32MB, halt,
  IDT 48 gates + PIC remap + PIT 100Hz + keyboard scancode map, `ticks/readkey/pmm_*`,
  ค่าแบบ tagged ชุดเดียวกับ hosted (Str/Bool/Null/List ใช้ได้จริงบน bare metal)
- `finally` รันทุกทางออกรวมถึง **error ที่เกิดใน `except` ของ try ตัวเดิม** — ทั้ง
  native (`hs.py build`) และ x64 (`hs_try_push0` ซ้อนเป็น handler ชั้นที่สอง
  แล้ว `hs_reraise`) ทำให้ตรงกับ interp; เทส regression อยู่ใน
  `tests/t_finally.hs`, `tests/x64/try.hs`, `kernel/ktry.hs`
- `kernel/xdemo.hs`, `kx2.hs` (timer/keyboard/PMM), `kxstr.hs` (Str บน serial),
  `kxlist.hs` (List: literal/append/index/`==`/`for`/`str()` บน serial),
  `kimp.hs`+`kmod_h.hs` (import + `mod.attr` บน bare metal),
  `kxexc_pf/de.hs` (EXC 14 / EXC 0), `ktry.hs` (try/except/finally/raise บน serial)
  `kxslice.hs` (slicing + split/find/join บน serial)
  + `tests/test_xkernel.py`: **62/62 ผ่าน**
- เหลือ: paging แบบไดนามิก (map/unmap page), frame allocator + `std.heap` ใน kernel,
  scheduler, filesystem, user mode

## 15. เอกสาร + tooling (เฟส 7 — v0.5.0 → v0.6.0)

เป้าหมายเฟสนี้: **ทุกคนและทุก AI เขียนภาษานี้เป็น** — เอกสารต้องไม่หลอก
(ทุกตัวอย่างต้องรันจริงได้) และ editor ต้องช่วยได้โดยไม่ต้องลง dependency

### 15.1 ชั้นข้อมูลเดียว (single source of truth)

- `scripts/lang_data.py` — keyword (28) + builtin (48) พร้อม signature,
  คำอธิบาย, และชุด backend ที่รองรับ (`interp`/`native`/`xbuild`/`xkernel`)
- `interp.BUILTINS` ยังคงเป็นความจริงฝั่ง runtime — `tests/test_docs.py`
  ยืนยันว่า table ครอบทุกตัวและไม่มีตัวลอย (`pmm_total`/`pmm_free`
  เป็นของ freestanding จึงอนุญาตเป็นตัวเดียว)
- `scripts/gen_api.py` อ่านสองแหล่งนี้แล้วเขียน `docs/api.json`
  (machine-readable) + `docs/builtins.md` (ตาราง markdown) — regenerate
  ได้ด้วยคำสั่งเดียว และเทสจะ fail ถ้าไฟล์ไม่ตรงกับ generator
- `scripts/gen_errors.py` ดึง `HSErr(...)` ทุกตัวจาก `interp.py`/`hs.py`/
  `x64gen.py`/`fmt.py` ด้วย AST แล้วเขียน `docs/errors.md` (351 ข้อความ)
  พร้อมตาราง "error ที่เจอบ่อย" — AI ใช้ grep หาสาเหตุได้ตรง ๆ

### 15.2 เอกสาร

| ไฟล์ | สำหรับ |
|---|---|
| `docs/index.md` | จุดเริ่ม + ตารางเลือกหัวข้อ |
| `docs/tutorial.md` | เขียนโปรแกรมแรก 10 นาที (ทุกบล็อกถูกรันจริง) |
| `examples/` | ตัวอย่าง 8 ไฟล์ครอบทั้งภาษา + `.expected` ทุกไฟล์ |
| `docs/stdlib.md` | `std.str` / `std.list` / `std.heap` |
| `docs/x64-subset.md` | ขอบเขต + กับดักของ backend ที่ไม่ใช้ gcc |
| `docs/kernel.md` | kernel freestanding |
| `docs/cheatsheet.md` | ทั้งภาษาในหน้าเดียว |
| `docs/errors.md` | ข้อความ error ทุกข้อความ (generate จาก source) |
| `docs/lsp.md` | language server + การต่อ editor |
| `docs/for-agents.md` | ทางลัด + เครื่องมือสำหรับ AI |
| `AGENTS.md` | กฎกระชับ (เป็น reference หลักของ agent) |
| `CONTRIBUTING.md` | กติกา/ขั้นตอนสำหรับคนที่จะเพิ่มภาษา |
| `SPEC-v1.md` | เหตุผลออกแบบ (ไฟล์นี้) |

`tests/test_examples.py` (**17/17**) บังคับว่าทุก `examples/*.hs`
ต้องรันได้จริง (interp) และตรงกับ native (gcc) — ตัวอย่างที่พังทำให้เทสแดง
และค้นพบบั๊ก parity จริง 2 บั๊ก (ดู §15.2 ประวัติ)

`tests/test_docs.py` (**38/38**) รันทุกบล็อก ```hs ใน `docs/*.md` เทียบกับ
บรรทัด `# =>` ตามลำดับ, เช็ค drift ของ `api.json`/`builtins.md`, เช็คว่า
ลิงก์ทุกอันใน README/`docs/index.md`/`AGENTS.md` มีไฟล์จริง, และสั่งคำสั่ง
ใน `docs/lsp.md` ว่ารันได้จริง — เอกสารจึงพังตามโค้ด

### 15.3 Language server (`lsp.py`)

- stdio + JSON-RPC เขียนด้วย stdlib ล้วน (ไม่มี pip dependency) เข้าผ่าน
  `python3 hs.py lsp` หรือ `python3 lsp.py`
- ฟีเจอร์: `textDocument/publishDiagnostics` (parse + scope check ทุกครั้ง
  ที่แก้ไฟล์/บันทึก), `hover` (builtin พร้อม backend, keyword, def/param/ตัวแปร,
  `mod.attr` พร้อมชี้ไฟล์ที่นิยาม), `completion` (keyword + builtin + ชื่อในไฟล์
  และเฉพาะชื่อระดับบนของโมดูลเมื่อพิมพ์ `mod.`), `definition`,
  `references` (ข้ามไฟล์ในโฟลเดอร์เดียวกัน + `HSPATH`),
  `documentHighlight`, `signatureHelp` (ผู้ใช้ + builtin, มี activeParameter),
  `documentSymbol`, `workspace/symbol`, `formatting` (เรียก `fmt.py`)
- ตำแหน่งใช้ UTF-16 code unit ตามสเปก LSP (ไทย/อีโมจิไม่เพี้ยน)
- `scripts/lsp_client.py` เป็น client แบบ one-shot เพื่อให้ agent เรียกใช้
  ได้โดยไม่ต้องค้าง server (`--diag/--hover/--def/--complete/--symbols/--format`)
- `tests/test_lsp.py` (**25/25**) ยิง protocol จริงผ่าน pipe

### 15.4 editor

`editors/vscode` (client.js ไม่ต้อง npm install), `editors/neovim`
(syntax/vim + `lua/holyshit.lua`), `editors/helix`, `editors/zed` —
ทุกตัวชี้ไปที่ `python3 <repo>/lsp.py` คำสั่งเดียวกัน

### 15.5 formatter เป็น gate จริง

`hs fmt --check` เทียบเฉพาะ "โครงสร้าง" (ไม่นับคอมเมนต์และบรรทัดว่าง เพราะ
printer พิมพ์คอมเมนต์ไม่ได้ — lexer ทิ้งไปแล้ว) และเปลี่ยนการ parse flag
ให้รับได้ทั้ง `fmt f.hs --check` กับ `fmt --check f.hs` ตอนนี้ทั้ง repo
เป็น canonical แล้ว และ `tests/test_fmt.py` ตรวจซ้ำทั้ง repo (ยกเว้น
`tests/fmt/*.hs` ที่ตั้งใจให้ไม่ canonical) — เทย์ก่อนแก้โค้ดแล้วเทสแดงถ้า
เพี้ยน

### 15.6 v0.6.0 — ขยาย LSP + เอกสารที่ generate ได้

- `resolve_parts()` ใน `lsp.py` เป็นตัวแก้ทางเดียวของชื่อแบบ dotted
  (hover/definition/completion/references/highlight/signature ใช้ร่วมกัน)
- เพิ่ม `references` (ข้ามไฟล์), `documentHighlight`, `signatureHelp`,
  `workspace/symbol`, completion หลัง `mod.`, hover บน `mod.attr` ที่ชี้ไฟล์
- บั๊ก parity 2 ตัวที่ตัวอย่างใหม่เผย: `finally` ถูกข้ามเมื่อ `except` handler
  raise — แก้ทั้ง native (`hs.py`) และ x64/kernel (`x64gen.py`)
- `docs/errors.md` generate จาก AST ของ source (351 ข้อความ)
- `tests/test_examples.py` บังคับให้ตัวอย่างทุกไฟล์รันได้จริง
- `hs fmt --check` ใช้งานได้จริง (เทียบโครงสร้าง ไม่นับคอมเมนต์) และทั้ง repo
  ต้อง canonical

### 15.7 สถานะเทสหลังเฟส 7

`test.py` 38 · `test_native.py` 39 · `test_fmt.py` 4 · `test_x64.py` 28 ·
`test_xkernel.py` 99 · `test_examples.py` 17 · `test_lsp.py` 25 ·
`test_docs.py` 38 (รันครบทุกชุด: `python3 tests/run_all.py`)

### 15.8 เตรียม OS: `load64`/`store64` (v0.6.1)

ฐานของงาน OS คืออ่าน/เขียน page-table entry ขนาด 64-bit จาก `.hs` ได้ — ก่อนนี้
`unsafe:` มีแค่ `load8/load32/store8/store32` ซึ่งตัดครึ่ง 64-bit ทิ้ง

- `load64(p)` / `store64(p, v)` ใน `interp.py` (ผ่าน `us_load/us_store` ที่เป็น
  size-generic อยู่แล้ว), `native/rt.c` (`hs_load64/hs_store64`) และ
  `x64gen.py` (`mov rax,[rax]` / `mov [rax],rcx` ไม่ผ่าน tag) — ทั้ง 3 backend
  ให้ผลเหมือนกัน เทส `tests/t_load64.hs` + `tests/x64/load64.hs`
- `hs fmt` เก็บการเขียนเลขฐานสิบหกไว้ (`0x83` ไม่กลายเป็น `131`) เพราะ flag ของ
  page table ต้องอ่านออก — parser เก็บ `raw` ของ literal, printer ใช้ตัวนั้น
- เทส: interp 36 · native 37 · x64 26 (เพิ่มไฟล์ใหม่ทั้งคู่)

### 15.9 bitwise operators (v0.6.1)

OS ต้องบิดขวดบิต (bitmap, page flags) ภาษาเดิมทำไม่ได้เลย รอบนี้เพิ่ม
`& | ^ << >>` กับ unary `~`

- ทั้ง 3 backend + error เดียวกัน: `operator 'OP' needs Ints, got A and B`,
  `shift count N out of range (0..63)`, `cannot bitwise-not T` (Bool ไม่ใช่ Int)
- ความสำคัญ: `or` < `and` < เทียบ < `+ -` < `* / %` < bitwise — bitwise ผูก
  แน่นกว่า `+ -` (ตรงกับ C) และ parser มีชั้น `parse_bits` แยก
- x64: `shl/sar` ตาม cl, ตัดผลให้เหลือ 62-bit signed (bit 61 เป็นบิตเครื่องหมาย)
  จึงมี divergence ที่บันทึกไว้: `1 << 61` เป็นลบบน x64 แต่เป็นบวกบน interp
- `hs fmt` เพิ่ม precedence + เว้นวรรคให้ `& | ^ << >>` และเก็บวงเล็บเมื่อ
  จำเป็น (`a & (b | c)`) — กฎเดิมคือ flatten ได้เฉพาะ `+`/`*` ฝั่งขวา
- เทส: `tests/t_bits.hs` (interp+native), `tests/x64/bits.hs` (x64)
### 15.10 memory management จริงบน bare metal (v0.6.2)

paging แบบไดนามิก + frame allocator จริง เขียนเป็น `.hs` ล้วน บูตจริงบน QEMU

- `kernel/kmb.hs` — อ่าน memory map ของ bootloader รองรับ 2 ABI (ตรวจโดย
  validate): spec multiboot1 กับ struct 88-byte ของ QEMU เอง (layout ไม่ตรง
  spec — QEMU ใช้ `mb_buf_phys` ของตัวเอง, entry 20-byte ที่ `0x9000`)
- `kernel/kpage.hs` — page table 4 ระดับ (`map`/`unmap`/`translate`,
  `map_phys`/`map_user`): สร้างตารางที่ขาด, แยก huge page (2MB/1GB) เป็น
  512 children, flush TLB (`invlpg` + `tlb_flush` ทั้ง TLB หลัง split)
- `kernel/kpmm.hs` — bitmap frame allocator บน region usable ที่ใหญ่สุด
  (ผ่าน `std.bitmap`), reserve image/heap/bitmap, `alloc`/`free`/`free_run`
- primitive ใหม่ใน `x64gen.py`: `mb_magic()`, `image_end()`, `tlb_flush()`
  (บวกของเดิม `mb_info`/`cr2`/`cr3`/`set_cr3`/`invlpg`); `mov_ri64` รับเต็ม
  64-bit (kernel ต้องการทุกบิต เช่น `0xDEADBEEF...`)
- บั๊กที่เจอระหว่างทาง (แก้หมด): `0x83` บน PTE 4K เปิดบิต PS (huge) ต้องใช้
  `0x03`; `pte_addr` ใช้ parent index อ่านตารางลูกหลัง split; `free_run`
  เรียก `reserve` แทนที่จะ release; `unmap` คืน `false` ใน `unsafe:` กลายเป็น
  Int 0 (ต้อง return ที่ safe level)
- เทส: `kprim` (primitives), `kpaging` (30 asserts: map/translate/split/unmap),
  `kpmmtest` (pool เต็ม + คืน pool) — xkernel 62 -> 77 เคส
### 15.11 kmalloc + address spaces (v0.6.3)

m2 ของงาน OS: heap ที่ขยายได้จริง + PML4 ใหม่ต่อ space — `.hs` ล้วน บูตจริง

- `std/heap.hs` เพิ่ม `heap_init_at(addr, nbytes)` (ของเดิม `heap_init` ไว้
  เหมือนเดิม): kernel map เฟรมก่อนแล้วค่อยเริ่ม free list บนนั้น
- `kernel/kheap.hs` — `init(npages)` เอาเฟรมต่อกันจาก PMM, `map_range` ไว้ที่
  `0x60000000`, แล้ว `malloc`/`free` ธรรมดา (reuse กลางลิสต์, รวมบล็อกกลับ,
  ขอเกินคืน 0 ไม่พัง)
- `kernel/kaddr.hs` — `new()` ก็อปทุก entry ที่ present ของ PML4 ปัจจุบัน
  (kernel อยู่ slot 0 ทั้งหมด), `switch()` โหลด CR3 (flush TLB ในตัว);
  user page ต้อง `>= 0x8000000000` (slot 1+) จึง isolated จาก space เดิม
- บั๊ก x64 ที่เจอ: global ที่ถูก assign ดิบใน `unsafe:` ของฟังก์ชันหนึ่ง แต่ถูก
  อ่านในอีกฟังก์ชัน โดน unbox ผิด (`raw_names` อยู่แค่ scope ละฟังก์ชัน) —
  ตอนนี้สะสมชื่อ raw ระดับโมดูลด้วย; อาการคือ `x_tname` เดินเข้าหน่วยความจำ
  ขยะจน `x_malloc` หมด ("out of memory" ปลอม)
- เทส: `kheaptest` (malloc/free/reuse/patterns), `kaddrtest` (switch แล้ว
  serial ยังออก, map ใน space ใหม่, เก่าไม่เห็น, กลับมาแล้วยังอยู่) —
  xkernel 77 -> 87 เคส
### 15.12 cooperative tasks ใน ring 0 (v0.6.4)

scheduler แบบ yield (ยังไม่ preemptive): policy `.hs`, กลไก encoder

- `kernel/ktask.hs` — `spawn(func)`/`run()`/`yield()`/`exit()` บน queue
  round-robin (ลิสต์คู่ขนาน ctx+state); entry คือ Func `f()` ธรรมดา
  (closure ได้ — caps ไปกับ r15); ต้องจบด้วย `exit()` มิฉะนั้น corpse ถูก
  schedule ซ้ำ (documented, ไม่ guard)
- กลไกใน `x64gen.py`: `ctx_swap` (save/load callee-saved + rsp + rip แล้ว
  jmp ไป rip ใหม่), `task_run` (จำ sched ลง slot ให้ task ที่ return),
  `task_init` (zero regs, r15 = func+16, rip = func code, วาง `task_exit`
  เป็น return address), stub `task_exit` (สลับกลับด้วย sched ที่จำไว้)
- บั๊กใหญ่ที่เจอ: `image_end` ไม่รวม main stack (16KB) — PMM แจกเฟรมทับ
  stack ทำให้ locals/return address พัง อาการโผล่ไกลเป็น wild jump
  (`EXC 6`), error ผี (`index must be Int` ทั้งที่ค่าถูก), ขึ้นกับ layout —
  ตามด้วย disassembly เทียบกับ Python อยู่นานก่อนเจอ; EXC report ตอนนี้
  พิมพ์ fault RIP + CR2 แล้วเลยไม่ต้องเดา
- เทส: `ktasktest` (3 task สลับกันใช้ counter ร่วม, exit ครบ, กลับ main) —
  xkernel 87 -> 94 เคส
### 15.13 preemptive scheduler (v0.6.5)

timer IRQ0 พา tasks สลับกันเอง: stub + tick handler `.hs` + switch ใน stub

- `kernel/ktask.hs` — `tick()` (อ่านอย่างเดียว ไม่ print/alloc) ครบ quantum
  คืน block เป้าหมาย, `preempt_on/off()`, `npreempted(i)` นับการถูกสลับออก;
  `spawn`/`exit` ครอบ mutation ด้วย `irq_off/on`
- กลไกใน `x64gen.py`: stub เซฟเต็ม 15 regs + rsp + rip (ห้ามแตะ rflags),
  เรียก handler บน stack เดิม (bounded, nest-safe), คืนค่า Null = restore +
  iret, คืนค่า block = บันทึก + full-load + กระโดด (rip จับคู่ rsp เสมอ:
  fresh -> entry, preempted -> tick_back + iret, suspended -> resume + ret);
  `irq_off/on`, `sched_on_tick(f)`/`sched_tick_clear()`, depth counter กัน
  nested tick (skip ไม่แตะ slot)
- บั๊กใหญ่ที่เจอ: IDT ใช้ interrupt gate (0x8E) CPU จึง clear IF ตอนเข้า
  stub แต่ switch path แบบ jmp ไม่เคย restore — task แรกที่ถูก preempt
  เลยวิ่งแบบหูหนวก (IF=0) จน `exit()` มา sti ให้; อาการคือ spans ยุบเป็น tick
  เดียวทั้งที่ count ครบ; ตามด้วย IF-sampling + PIC/APIC/monitor จนเจอ;
  เติม `sti` ก่อนกระโดดแล้วหาย
- บั๊กที่สอง: `ctx_swap_inner` เก็บแค่ callee-saved — task ที่ถูกปลุกด้วย
  cooperative load ได้ caller regs เก่ามั่ว (count หายแบบเงียบ); ตอนนี้
  full save/load ทั้ง inner และ stub (ใช้ push_m + ret เพราะไม่มี scratch
  reg ว่าง)
- เทส: `kpreempt` (hog ไม่ yield แต่รอด้วย ticks เองจนโดนสลับแน่ๆ + นับ
  ตรง + โดนสลับทุกตัว) — xkernel 94 -> 99 เคส
### 15.14 filesystem: ramdisk + VFS (v0.6.6)

ระบบไฟล์แรกของ OS — ทั้งหมดเป็น `.hs` ล้วน ไม่มี block driver

- builtin ใหม่ `read_mem(ptr, n)` → Str ของไบต์ดิบ (byte-preserving) บนทุก
  backend; ของเดิมอ่าน memory ได้แค่ทีละไบต์/word ใน `unsafe:` ซึ่งเอาไป
  ต่อ string ทั่วไปไม่ได้ — kernel ต้องอ่าน struct ของ bootloader เป็นชิ้น
  (ต้องมี Str เพราะ `path` ใน KRFS เป็น bytes ไม่ใช่ตัวเลข)
- `kernel/kvfs.hs` — inode เป็นลิสต์ขนาน + bytes เป็น Str: `mkdir`/`mkdirs`
  (แบ่งชั้น), `create`/`write`(แทนทั้งไฟล์)/`read`, `ls`, `stat` →
  `[kind, size]|null`, `is_file`/`is_dir`, `unlink` (dir ต้องว่าง; inode ที่ยัง
  เปิดอยู่กลายเป็น dead → fd stale), fd layer `fopen`/`fread`/`fwrite`/`fseek`/
  `ftell`/`fclose`. ไม่มี cwd — resolve จาก root เสมอ, `.`/`..` ได้
  - ชื่อชั้น fd ขึ้นต้นด้วย `f` (`fopen` ไม่ใช่ `open`) เพราะชื่อ `open/read/
    write/close/mkdir/ls` คือ builtin ของภาษา: ต้องไม่ให้ `.hs` ไปชน
- `kernel/kramdisk.hs` + `scripts/mkramdisk.py` — อ่าน multiboot module
  (`kmb.mod_start/mod_end`) เป็น KRFS image แล้วแตกลง `kvfs`: ทุก field
  pad ขึ้น 4 ไบต์เพื่ออ่านด้วย `load32` อย่างเดียว (ไม่ต้องเชื่อ alignment),
  path เรียงตามความลึก → สร้างทั้ง tree ใน pass เดียว
- เทส: `tests/t_vfs.hs` (66 assertion บน interp + native) และ
  `tests/x64/vfs.hs` (x64 ต้องตรงกันเป๊ะ), `kernel/kfstest.hs` (บูตจริงบน QEMU
  พร้อม `-initrd`: โหลด 4 entry แล้วอ่าน/เขียน/ลบ)
### 15.15 บั๊กที่เจอระหว่างทำ filesystem (v0.6.6)

- ชื่อฟังก์ชันที่ชนกับ builtin: `kvfs.read(fd, n)` ถูก parse เป็นการเรียก
  builtin `read` (arity ผิด → error) เพราะ x64 เดิม emit builtin ก่อนเสมอ;
  แก้โดยให้ `def` ของผู้ใช้ shadow builtin (interp/native เป็นแบบนี้อยู่แล้ว)
  แต่ชื่อที่อยู่ในรายการ `XBUILTINS` ยังเป็น builtin เสมอ เพราะ capture
  analysis ข้ามชื่อเหล่านั้น (ถ้าไม่งั้น capture slot ไม่ถูกสร้าง)
- `image_end()` ต้องรวม **page tables ตอนบูต** ด้วย ไม่ใช่แค่ end ของไฟล์:
  ตารางอยู่หลัง `.data` ที่ page-aligned ถ้า `image_end` เล็กเกินไป PMM
  จะแจกเฟรมที่ยังใช้เป็นตารางอยู่ แล้ว heap ที่เพิ่ง init เขียนทับ → PDPT[0]
  เป็น 0 → `#PF` (เขียนใน bump heap ที่ 0x2008ca0) แล้ว handler เอง fetch
  fault ที่ 0x101dc1 → double/triple fault → reboot วนจน QEMU ตัดเวลา
  (อาการคล้าย Heisenbug: ย้ายโค้ดนิดเดียวก็หาย เพราะ layout เปลี่ยนว่าอะไร
  ทับกันบังเอิญ) — แก้แล้วเป็น `max(stack_top, end of tables)` + ย้าย main
  stack เข้า `.data` เพื่อไม่ให้ชนข้อมูลของ bootloader ที่ QEMU วางไว้
  หลัง image และกู้ `busy()` + assertion ใน `kpmmtest` เป็นกันดัก
- หน้าต่าง bump ของ runtime (`alloc()` → Str/List/page table/bitmap ที่
  `0x2000000` ขนาด 16MB) อยู่ใน pool ของ PMM ด้วย ต้อง reserve ออกไป
  ไม่งั้น kmalloc กับ bump allocator เขียนทับกันเงียบ ๆ (คนละคนคิดว่าจอง
  frame เดียวกันได้)
### 15.16 user mode + syscall (v0.6.7)

ring 3 จริง: kernel โหลด static ELF (`xbuild` ธรรมดา, ส่งเป็น multiboot
module) ขึ้นไปรัน แล้วรับ syscall ด้วย handler `.hs`, เสร็จกลับมา kernel —
ทั้งหมด `.hs` ล้วน (กลไก encoder) ไม่มี C

- `kernel/kuser.hs` — ELF loader: เดิน program header, `map` ทุก `PT_LOAD`
  ที่ `vaddr + USER_BIAS` (PML4 slot 1+; ฝั่ง kernel เป็น supervisor-only),
  เปิด writable ก่อนแล้ว `protect` text กลับเป็น read-only (W^X), stack 8
  เพจ; `run()` = `enter_user(entry, frame)`
- `kernel/ksyscall.hs` — `dispatch(nr, a1..a6)`: write (fd 1/2 → serial),
  mmap (anonymous, kernel เลือก address), exit (จำ code + `user_stop()`);
  exit code เป็น opaque (tagged อยู่แล้วใช้เลย, Null → 0)
- stub ใน `x64gen.py`: park/tag/handler/untag เหมือนเดิม แต่ stack เป็น
  syscall stack 16KB ของตัวเอง (ไม่ไว้ใจ user rsp) และขากลับเป็น `sysret`
  (คืน rcx/r11/rsp จาก slot); `user_stop()` กลับทาง `user_cont_` บน stack
  เดิม; `enter_user` ต่อด้วย `sti` (path นี้มาแบบ IF=0 แต่ kernel วิ่ง IF=1)
- เทส: `kring3` (exit), `kring3ret` (sysret กลับแล้ว hlt fault ด้วย USER
  rip + CS=0x23), `kring3wr` (write ออก serial แล้ว exit),
  `kusermode` (ELF จริงพิมพ์ครบ exit 0 กลับมา kernel) —
  xkernel 105 -> 126 เคส; `tests/x64/asptr.hs` กันดัก `as_ptr`/`as_int`
  ข้างล่าง — รวม 322 เคส ผ่านหมด
### 15.17 บั๊กที่เจอระหว่างทำ user mode (v0.6.7)

- `syscall` ไม่ใช่ interrupt: CPU เซฟแค่ rip→rcx กับ rflags→r11 ไม่ push
  frame ไม่สลับ stack — stub เวอร์ชันแรกทำเหมือน IRQ (park ใต้ "frame"
  40 ไบต์ที่ไม่มีจริง + กลับด้วย `iretq`) เลย pop ขยะ: ทำ park ทับ user
  stack ตัวเอง, `iretq` อ่าน RIP/CS ขยะ (`EXC 13` บ้าง `#PF` บ้างตามขยะ);
  ระหว่างดีบักเคยสงสัยว่า EXC reporter อ่าน RIP ผิด slot (นับ stack ได้
  136 แทน 128) แต่ disassembly พิสูจน์ว่า 128 ถูกตั้งแต่แรก — บทเรียน:
  verify ด้วย objdump ก่อนโทษ reporter, และอย่าอ่าน serial ตอน QEMU
  โดน terminate (เห็นครึ่งเดียวแล้วตีความผิด);
  สรุป: `syscall` เข้า (rcx/r11, ไม่แตะ stack), กลับด้วย `sysret`
  (ไม่มี frame ให้ pop), IRQ/fault เท่านั้นที่ใช้ TSS + iretq
- `as_ptr(x)`/`as_int(x)` กับตัวแปร unbox ซ้ำ: `sev()` แปลง dynamic slot
  เป็น raw word แล้ว `as_*` เช็ก tag + shift อีกรอบ — pointer ที่ low bits
  ไม่ใช่ 00 โดน reject/shift ผิด; แก้ให้ `is_raw_expr` คืน True กับ `var`
  (อ่านครั้งเดียวพอ) + เทส `tests/x64/asptr.hs`
- `pte_addr` สร้างตารางชั้นกลางแบบ supervisor เสมอ: user page ได้ leaf
  เป็น user แต่ทางผ่านเป็น supervisor เลย fault ตั้งแต่ `iretq` แรก —
  ต้องพา U/S bit ลงไปทั้ง path (ตารางเก่าอัปเกรดตอนเจอครั้งแรก)
- GDT user descriptor ผิด: `| 3` ได้แค่ limit bits ไม่ได้ DPL — DPL ยัง 0
  `iretq` ไป ring 3 เลย `#GP`; ต้อง access byte 0xF2/0xFA (DPL=3) จริง
- `EFER` เขียน `or eax, 0x100` ได้แค่ LME (bit 8) ไม่ได้ SCE (bit 0) —
  `syscall` เป็น `#UD` ทั้งที่ MSR "เขียนแล้ว"; ต้อง `0x101`
- `IA32_LSTAR` คือ `0xC0000082` ไม่ใช่ `0xC0000080` (นั่น EFER — เขียนทับ
  แล้ว paging พัง), `EDX` ต้องเคลียร์ก่อน `wrmsr` (MSR 64-bit)
- `sysret` ไม่มี REX.W คือ compat-mode (CS = STAR base เป็น data selector
  `0x13`, fetch แตกทันที); ต้อง `48 0F 07` จึงได้ CS=0x20/SS=0x18
- ครึ่ง sysret ของ `STAR` ต้อง base `0x10` (ได้ CS=0x20/SS=0x18) ไม่ใช่
  `0x18`; เพิ่ม `FMASK=0x200` (mask IF ตอนเข้า) กันอนาคตที่มี IF=1
- โปรแกรมมือ (hand stub) เขียน `48 B8` (movabs **rax**) แทน `48 BE`
  (movabs rsi) — ทับ syscall number ตัวเองด้วย address เลยได้ ENOSYS
  เงียบ ๆ; กันดักคือ assert ไบต์ทุกตัวแบบ `kring3` (เคสนี้สอนให้ assert
  ตั้งแต่ `mov eax,1` ตัวแรก ไม่ใช่แค่ส่วนหลัง)
### 15.18 shell ใน ring 3 + syscall ไฟล์ (v0.6.8)

user ต่อ VFS ผ่าน syscall ตัวเลขเดียวกับ Linux — path เป็น `(ptr, len)`
เพราะ Str ของ hs ไม่มี NUL:

| nr | syscall | ทำอะไร |
| --- | --- | --- |
| 0 | `read(fd, buf, len)` | fd 0 = keyboard (หนึ่งบรรทัด), อื่น ๆ = ไฟล์ |
| 1 | `write(fd, buf, len)` | fd 1/2 = serial, fd 3+ = เขียนไฟล์ |
| 2 | `open(path, len, flags)` | 0 = อ่าน, อื่น ๆ = เขียน → fd user = kvfs + 3 |
| 3 | `close(fd)` | |
| 59 | `exec(path, len)` | โหลด ELF จาก VFS ทับ image เดิม |
| 78 | `ls` / 83 `mkdir` / 87 `unlink` | ผ่าน `kvfs` ตรง ๆ |

- `kernel/ksyscall.hs`: `copy_out(dst, s, n)` คัด Str ลง user memory,
  `readline()` spin `readkey()` หลัง `irq_on()` (path syscall มาแบบ IF=0
  คีย์บอร์ดไม่มาให้), backspace = byte 8 ที่สร้างครั้งเดียวจาก `alloc`
  (escape ของ hs ไม่มี `\0..\8`)
- `exec` ใช้ `exec_enter` (iretq ที่ไม่บันทึก continuation) แยกจาก `run()` —
  ถ้าใช้ `run()` มันทับ continuation/stack ของ session เดิม
- `scall(nr, a1..a6)` = builtin ใหม่ของ x64 hosted (ส่ง `syscall` ตรง ๆ,
  คืนค่าเป็น Int) ให้ `kernel/uush.hs` = shell ใน ring 3 (`help echo cat ls
  mkdir rm write run exit`) เขียนด้วย hs ล้วนเหมือนกัน
- เทส: `kiotest` (เรียก syscall ไฟล์จาก ring 0 ตรง ๆ — deterministic ไม่ต้อง
  พิมพ์คีย์), `kushtest` + shell session จริงสองรอบบน QEMU
  (`caa\x08t /motd` แก้คำด้วย backspace, `write`+`rm`, `run /nope` แล้ว
  `run /bin/hi`) + `tests/x64/scall.hs` — x64 31 -> 32 ชุด,
  xkernel +145 assertion (รวม 274)

### 15.19 บั๊กที่เจอระหว่างทำ shell (v0.6.8)

- `copy_out(buf, s)` เรียก `len()` ของ Str แต่ arity ไม่ถูกตรวจ (ช่องว่าง
  ใน x64 subset) → `n` ที่ไม่ได้ bind เป็น Func → `cannot compare Int and
  Func` — ผ่าน `kiotest` จับได้ทันทีเพราะไม่ต้องเดา timing
- resume กลับจาก ring 3 ต้องคืน **rbp** ของเฟรมที่ `enter_user` ถูกเรียก:
  ตอนนั้น stub ทำงานบน syscall stack และ rbp เหลือเป็นของ handler (หรือของ
  ring 3) ทำให้ epilogue `mov rsp,rbp; pop rbp; ret` พุ่งไปที่ไหนแล้ว
  triple fault = reboot เงียบ ๆ (เห็นเป็น "บูตใหม่" ใน serial) — บันทึก
  `user_saved_rbp_` ตอนเข้าและคืนค่าก่อน `jmp` ที่ continuation
- `sendkey` ของ QEMU เงียบไปเองตอนพิมพ์เร็วเกิน (PS/2 overrun ทิ้ง key)
  ทำให้ session ไม่ deterministic — ต้อง reply-check ทุกครั้ง ช้า 0.6s/ตัว
  และอย่าเริ่มพิมพ์ก่อน shell ขึ้น (จอแรกเป็น 15s)
### 15.20 ปิดช่องโหว่ syscall + หนี้ docs (v0.6.9)

- `user_range_ok(addr, n)` ใน `ksyscall`: pointer จาก ring 3 ต้อง `>=
  USER_BIAS` ไม่งั้นคืน `-EFAULT` (14) โดยไม่แตะ memory — เดิม `read_mem`
  /`copy_out` อ่าน/เขียน address ไหนก็ได้ (info leak + corrupt kernel จาก
  ring 3); `kiotest` เลยต้อง poke path/buffer ลง user page จริงแทน
- `copy_out`/`sys_read` fd 0 กัน `n <= 0` คืน 0 ก่อน (เดิม `n` ลบหลุดเป็น
  return ติดลบ และ fd 0 จะเข้า `readline()` แล้วค้าง)
- จดไว้เป็นข้อจำกัด: `write` fd 1/2 ผ่าน `print` จึงแถม `\n` เสมอ
  (byte-exact ต้องมี builtin serial-write ตัวใหม่ — ยังไม่ทำ)
- error message กลับเป็น literal: `enter/exec_enter wants ...` แยกสอง
  บรรทัด, `unknown variable` ใช้ string concat (ไม่เพิ่ม template ใหม่) —
  `docs/errors.md` กลับมามีชื่อจริงแทน `{name}/{ar['name']}`
### 15.21 arity check ใน x64 (v0.6.10)

x64 ไม่เคยตรวจจำนวน arg: เรียกผิดแล้ว callee อ่านขยะจาก stack ได้ error
มั่ว (`cannot add Int and Func`) — interp/native ดักได้ตั้งแต่แรก
(`f wants 2 args, got 1`) ตาม native ที่เก็บ `name+arity` ใน Func object:

- Func เป็น `[kind][code][nparams][name][caps...]` (caps ขยับ +16 → +32
  ทั้ง 4 จุด: call site, task_init, tick stub, syscall stub)
- ทุก user call เทียบ `nparams` กับจำนวน arg จริง; ผิดทาง cold helper
  `arity_fail` ประกอบ `"NAME wants N args, got M"` จาก struct (ไม่ใช่ชื่อ
  静态) แล้ว `hs_raise_msg` — `f = g; f(1,2)` รายงาน `g` ตรง interp,
  try จับได้
- `task_init`/`sched_on_tick` ตรวจ 0 arg, `syscall_register` ตรวจ 7 arg
  ตั้งแต่ตอน register (stub ร้อนไม่ต้องตรวจซ้ำ)
- เทส: `tests/arity` (interp+native), `tests/x64/arity`,
  `tests/x64/arity_reassign` — kernel ทั้งหมดบูตผ่านเหมือนเดิม
  (kiotest + shell session `fails 0`)
