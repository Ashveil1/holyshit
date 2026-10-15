# holyshit — SPEC v1.0 (ภาษาใหม่: dynamic + indent + ปลายทาง native)

> สถานะ: v0.6.30 — ภาษา + 4 backend (interp / native gcc / x86-64 ตรง /
> kernel freestanding) + IR กลาง + stdlib + formatter + language server + เอกสารที่เทสตรวจ
> หลักการ: เขียนง่ายกว่า Python, รันทันทีแบบ JIT workflow, แกน dynamic เต็มตัว,
> งาน low-level อยู่ใน `unsafe` เท่านั้น, syntax พังจาก v0.3 ได้ (v0.3 เก็บไว้เป็น legacy)

## 1. Lexical

- ย่อหน้า (indent) มีความหมายแบบ Python: block เริ่มหลังบรรทัดที่ลงท้าย `:`
- indent ต้องสม่ำเสมอใน block เดียวกัน (แนะนำ 2 หรือ 4 ช่อง, ห้าม tab นำหน้า)
- ไฟล์สคริปต์ใช้นามสกุล `.hs`, รันด้วย `python3 interp.py prog.hs`
- block (if/while/for) ไม่สร้าง scope ใหม่ — มีแค่ function เท่านั้นที่สร้าง scope (แบบ Python)
- จบ statement ด้วยขึ้นบรรทัดใหม่ (`;` ใช้ไม่ได้แล้ว)
- คอมเมนต์: `#` และ `//` ถึงท้ายบรรทัด
- string: `"..."` มี escape `\n \t \r \0 \" \\` (escape ที่ไม่รู้จัก
  ปล่อยผ่านมาเป็นตัวอักษร), ไม่มี string หลายบรรทัดใน v1
- เลขทศนิยมเขียนเลขยกกำลังได้: `1.5e3`, `2.5E-2`, `1e3`, `.5e1` (และคงรูป
  เดิมไว้เวลา `hs fmt`)

## 2. ค่า (dynamic ทั้งหมด, ไม่มีประกาศ type)

| ชนิด | ตัวอย่าง | หมายเหตุ |
|---|---|---|
| Int | `42`, `-7`, `0xFF` | 64-bit signed |
| Float | `3.14`, `2.0`, `1.5e3` | 64-bit; repr คือ shortest round-trip |
ติดกับ `print`/`str` เหมือน Python (`0.1` ไม่ใช่ `0.10000000000000001`) |
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
- ตรรกะ: `and or not` (short-circuit ยกเว้น backend x64), truthiness: `false null 0 "" [] {}` เป็นเท็จ ที่เหลือจริง
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
- `for i in range(a, b, s)` (s ลบได้): parse-time desugar เป็น `range(0, N)` + `i = a + k*s`; a,b,s ประเมินครั้งเดียว; s == 0 = division by zero; ใช้ได้เฉพาะใน `for`

## 5. Builtins ชุดแรก (v1)

- `print a, b, ...` → คั่นช่องว่าง + ขึ้นบรรทัดใหม่ (เหมือน v0.3), `print` ว่างๆ = บรรทัดเปล่า
- `len(x)` → ความยาว Str/List/Dict
- `range(n)`, `range(a, b)`
- `str(x)`, `int(x)`, `float(x)` แปลงชนิด (แปลงไม่ได้ = error)
- `input()` อ่าน 1 บรรทัดจาก stdin → Str
- File (น้อยสุดที่พอใช้): `open(path, mode)` + `read(f)` + `write(f, s)` + `close(f)` โดย mode `"r"`/`"w"`
- `len` ใช้กับ Dict = จำนวน key
- **Dict key (v0.7):** key เป็น `Str` หรือ `Int` (Bool/Float/อื่นๆ ขึ้น `dict key must be Str or Int`; Bool ไม่รับเพราะ `true == 1`). `{1: "a", "k": 2}`, `d[5] = x`. `json_str` ยังต้องการ key เป็น Str. ทุก backend (interp/IR/native/x64) ตรงกัน; แก้บั๊ก `==` ของ dict บน x64 ที่เคยตอบ true เสมอด้วย.
- String/List: `append(a, x)`, `split(s)` / `split(s, sep)`, `find(s, sub)` (-1 ถ้าไม่เจอ),
- **Method sugar (v0.7):** `x.append(v)`, `s.split(sep)`, `s.find(sub)`, `sep.join(list)` เขียนแบบ
  method ได้ แปลงตอน parse เป็น `append(x, v)` ฯลฯ ทุก backend เห็นการเรียก builtin ธรรมดา
  (formatter คงรูป method ไว้). ถ้า receiver เป็น path ที่ขึ้นต้นด้วยโมดูลที่ `import` ไว้
  (`std.heap.find(...)`) ยังหมายถึงฟังก์ชันของโมดูลตามเดิม.
  `join(sep, list)`, slice `s[a:b]` / `s[:b]` / `s[a:]` (list ก็ได้, index ติดลบได้)
- **lambda (v0.7):** `lambda x, y: expr` (ไม่มี body หลายบรรทัด) แปลงตอน parse เป็น `def _lamN` ที่ยกขึ้นก่อน statement. formatter พิมพ์กลับเป็น `lambda`.
- **f-string (v0.7):** `f"x={x}, sum={a + b}"` แปลงตอน parse เป็น `"x=" + str(x) + ...`; `{{` `}}` = วงเล็บจริง; ใน `{}` ใส่ string literal ที่มี `"` ไม่ได้. formatter คงรูป f-string.
- **class (v0.7):** `class C:` + `def` ที่รับ `self` เป็น param แรก, `__init__` เป็นตัวสร้าง. แปลงตอน parse: แต่ละ method เป็นฟังก์ชัน `C__m`, `C(args)` คือฟังก์ชันที่สร้าง dict `{"m": C__m, ...}` แล้วเรียก `__init__`; `o.f` = `o["f"]`, `o.f = v` = `o["f"] = v`, `o.m(x)` = `o["m"](o, x)`. inheritance แบบเดี่ยว `class D(B):` (คัดตาราง method ของ B มาก่อน แล้ว override; `__init__` สืบทอดถ้าไม่เขียนเอง; เรียก init ของแม่ด้วย `B__init__(self, ...)`; B ต้องประกาศก่อน). ข้อจำกัด: ไม่มี super()/multiple inheritance; ชื่อ method ห้ามซ้ำ builtin sugar (`split find join append`); receiver ของ `o.m()` ต้องเป็นชื่อหรือ field (`a.b.m()` ได้, `f().m()` ไม่ได้ ให้เก็บใส่ตัวแปรก่อน); `x = some_module` ยังเป็นโมดูล (ตามชื่อโมดูลที่ import). object พิมพ์แล้วเห็น dict ของ method ด้วย.
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
- struct by pointer ทำได้: `malloc` แล้ว `store*/load*` ใน `unsafe:` ตาม offset (tests/t_ffistruct.hs ใช้ `gmtime_r` เติม `struct tm`) — โปรแกรมที่มี `extern` เท่านั้นที่ load/store ที่อยู่จริงของ C ได้ (interp ใช้ ctypes), ไม่มี extern ยังเป็น arena จำลองตรวจขอบเขต
- ทำไม่ได้: struct by value, callback, variadic (เช่น `printf` ตรงๆ) — เขียน wrapper C ครอบเอา
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
### 15.22 hosted เติบโต: argv/input/env บน x64 (v0.6.11)

โปรแกรม `xbuild` อ่านโลกภายนอกได้แล้ว (ก่อนหน้านี้ได้แค่คำนวณ+พิมพ์):

- `_start` เก็บ argc/argv ลง slot ก่อน align stack (entry: `[rsp]=argc`)
- `argv()` = List ของ `argv[1:]` (ข้ามชื่อโปรแกรมเหมือน interp),
  `input()` = หนึ่งบรรทัด (byte-at-a-time เพราะไม่มี pushback,
  EOF เปล่าๆ = `input: EOF`), `env(name)` = สแกน envp หา `NAME=` (ขาด =
  null) — ทั้งหมดผ่าน raw syscall/Tempered stack ไม่มี libc
- `test_x64.py` รู้จัก `.args`/`.stdin` แล้ว และส่ง `.env` ให้ตอนรัน
  (เดิม overlay มีผลแค่ตอน build) — เทส: `argv`, `input`, `input_eof`,
  `env` (x64 34 -> 38 ชุด)
- เหลือ: `open/read/write/close` (ต้องมี heap kind `K_FILE`),
  `system` (ต้องมี process), Float/Dict/extern/attr บนค่า
### 15.23 hosted file I/O: open/read/write/close บน x64 (v0.6.12)

- heap kind ใหม่ `K_FILE` (`[kind][fd][flags][path]`) + `print`/`str`
  แสดง `<file PATH>` + `tname` รู้จัก `File`
- `open(path, "r"/"w")` ผ่าน `openat` (w = O_WRONLY|O_CREAT|O_TRUNC),
  `read` อ่านทั้งไฟล์แบบ grow, `write` วนจนครบ (คืน byte count),
  `close` เป็น no-op เมื่อปิดแล้ว — error เป็น `errno N`
  (ต่างจาก interp ที่โชว์ strerror; จดไว้)
- เทส: `file` (เขียน/อ่าน/โชว์/เทียบ), `file_err` (ENOENT),
  `file_errmode` (mode), `file_closed` — รวมไฟล์ 100KB ผ่าน
  (x64 38 -> 42 ชุด)
- เหลือ: `system`, Float/Dict/extern/attr บนค่า
### 15.24 system() บน x64 (v0.6.13)

- `system(cmd)` ผ่าน fork + execve(`/bin/sh -c cmd`) + wait4 ล้วนๆ
  (env ส่งต่อของเดิม, exec ล้ม = 127, โดน signal = ลบเหมือน Python)
- เทส: `system` (exit 3/0 + kill -9 → -9) — x64 42 -> 43 ชุด
- เหลือจริงๆ: Float (ต้องเปลี่ยน representation), extern, attr บนค่า
### 15.25 module alias บน x64 (v0.6.14)

- `m = mod` / `m = pkg.sub` ผูกชื่อโดยไม่ emit โค้ดเลย; `m.attr` เรียก
  ได้เหมือนของเดิม (รวม error `has no attribute` และ `print m`)
- กฎ nearest-wins: value slot ใน scope ที่ใกล้กว่าชนะ (param/def/capture
  บัง import ได้เหมือนเดิม), เสมอกันใน scope เดียวกันให้ binding ชนะ
  (เพราะ scope ของ x64 เป็น flow-insensitive), assign ค่าปกติทับ alias
  ได้ (`m = 42` หลัง `m = mod` กลายเป็นค่าปกติ)
- ส่งโมดูลเข้า call/operator/index ยังเป็น error เหมือนเดิม
  (`err_mod_value` เปลี่ยนเป็น `print x + 1`; เพิ่ม `modalias`)
  — x64 43 -> 44 ชุด
- เหลือจริงๆ: Float/Dict/extern/attr บนค่า
### 15.26 _start อ่าน argc พังบน stack ของ kernel (v0.6.15)

- v0.6.11 ใส่ `_start` capture (อ่าน argc จาก `[rsp]`) — บน Linux ถูก
  แต่โปรแกรมที่ kernel โหลดไม่มี argc บน stack: อ่าน word นอก map ทันที
  → `EXC 14` ตั้งแต่คำสั่งแรกของ user (`kusermode`/`kushtest` พังทั้งหมด
  ทั้งที่ kiotest ผ่าน — kiotest ไม่เข้า ring 3)
- matrix พิสูจน์: kernel เก่า + user ใหม่พัง, kernel ใหม่ + user ใหม่พัง,
  kernel เก่า + user เก่าผ่าน → ของเสียอยู่ฝั่ง user ELF (hosted emission)
- แก้ที่ `build_frame`: วาง argc=0 กับ argv[0]=NULL บนยอด user stack
  แล้วเริ่ม rsp ต่ำลง 16 (frame ขยับลงกันทับ) — `argv()` ว่าง, `env()`
  เจอ NULL เป็น null ถูกต้อง
- บทเรียน harness: binary โต + TCG ช้า รอ 10s เห็น serial ขาดกลางทาง
  แล้วดูเหมือน hang — ต้อง 25s; ปรับ `kusermode` timeout 15 → 25

### 15.27 Dict ใน x64 (v0.6.15)

ปิดช่องโหว่ตัวสุดท้ายของ subset: Dict ที่เคยเป็น compile error

- heap kind ใหม่ `K_DICT` = `[kind][len][cap][buf]` โดย buf เก็บคู่
  (key, value) สลับกัน — หนึ่งคู่ 16 ไบต์ จึงเดินด้วย word index
  (เลขคู่) และ `for k in d` ข้ามทีละ 2
- ค้น key แบบ linear scan (`x_str_cmp`) — dict ในภาษานี้เล็ก และลำดับ
  insertion คือสิ่งที่ interp (Python dict) โชว์อยู่แล้ว; เขียน key เดิม
  ทับของเดิมไว้ที่ตำแหน่งเดิม (Python semantics)
- `x_dict_new` เตรียมเป็นจำนวนคู่ตายตัว (รู้ตอน compile) แล้ว `x_dict_set`
  โตเป็น 2 เท่า/ครั้ง (คัดลอกด้วย copy_bytes)
- literal `{"k": v}` ประกอบใน stack: push ทุกคู่ตามลำดับต้นฉบับ แล้ว
  อ่านกลับด้วย offset คงที่ (`16*(n-i)`) เพราะ pop แบบ LIFO จะเดินกลับ
  ลำดับ — บันทึกเป็น gotcha ไว้ในโค้ด
- `x_dict_get` ขึ้น `key 'k' not found`, `d[1]` ขึ้น `dict key must be Str`
  (ตรวจชนิด key ก่อนชนิด index ตามลำดับของ interp)
- `x_dict_eq` คืน 0 เมื่อเท่า (เหมือน `x_list_eq` — `x_eq` แปลงด้วย
  `sete` สลับกันแล้ว `==` จะกลับด้านเงียบๆ)
- เทส `dict` (17 เคส รวม nested/equality/order), `dict_missing`,
  `dict_keytype` — x64 44 -> 47 ชุด; kernel บูตผ่านเหมือนเดิม
  (kiotest `fails 0`)

### 15.28 builtin ใช้เป็นค่าใน x64 (v0.6.15)

`f = str; f(65)` เคยเป็น compile error เพราะ x64 ไม่มี trampoline

- อ่านชื่อ builtin ในตำแหน่ง value -> สร้าง Func object
  `[kind][code=bi_call][nparams=-1][name][caps[0]=id]` เก็บใน data slot
  ต่อชื่อ (cache) จึงเทียบตัวตัวเองได้เหมือน interp
- sentinel `nparams = -1` บอก call site ให้ข้าม arity check แล้วส่ง
  `argc` (rdi) + เลขบรรทัดของผู้เรียก (rsi) ไปให้ `bi_call`
- `bi_call` แตกตาม id แล้วเทียบ argc -> **tail jump** ไป stub ของ
  (builtin, argc) ที่ emit ปลายโค้ด: stub ไม่สร้าง frame ใหม่ เพราะ
  frame ของ `bi_call` มี argument อยู่ที่ `[rbp+24]` อยู่แล้ว — stub
  อ่าน argument ในที่แล้วปิด frame ของ bi_call (`mov rsp,rbp; pop
  rbp; ret`) ทำให้ inline emitter เดิมใช้ซ้ำได้โดยไม่แตะ
- argc ผิด -> ข้อความตาม interp (`str wants 1 arg, got 2`) พร้อม
  เลขบรรทัดของผู้เรียก
- `print`/`str` ของ builtin เป็น `<builtin NAME>`; `tname` เป็น `Builtin`
  (Func ที่ประกาศเองยังเป็น type error ตามเดิม)
- stub emit เฉพาะ builtin ที่โปรแกรมอ้างจริง -> โปรแกรมที่ไม่ใช้เลย
  ไม่มีต้นทุนโค้ด; เทส `builtin_value` (ผ่านตัวแปร/ผ่าน argument ของ
  `def`), `builtin_value_arity` — x64 47 -> 49

### 15.29 file helpers ใน x64 (v0.6.15)

`read_text/write_text/append_text/exists/ls/mkdir` ที่เคยเป็น compile
error บน x64 — ตัวแกรม/สคริปต์ที่ใช้ไฟล์จึงรันบน backend นี้ได้แล้ว

- ทั้งหมดต่อยอดจาก File runtime ที่มีอยู่ (openat/read/write/close)
  บวก syscall ดิบอีกสามตัว: `access` (21) เป็น `exists`, `mkdir` (83)
  เป็น `mkdir`, `getdents64` (217) เป็น `ls`
- `open` ได้โหมดที่สาม = append (`O_WRONLY|O_CREAT|O_APPEND`) เพื่อให้
  `append_text` ได้
- `mkdir` ทำ makedirs เหมือน interp: เดินหา `/` ในพาธแล้ว mkdir ทีละ
  prefix (EEXIST ข้าม) แล้วค่อย mkdir พาธเต็ม — ต้องส่ง **payload** ของ
  Str เข้า `x_str_at` ไม่ใช่ตัว object (ได้ gotcha)
- `ls` อ่าน `linux_dirent64` แล้ว **สแกนหา NUL** เพื่อหาความยาวชื่อ
  (ห้ามใช้ `d_reclen - 19`: `d_reclen` ปัดขึ้นเป็น 8 ไบต์) ข้าม `.`/`..`
  แล้ว insertion sort ตาม `x_str_cmp` — เทียบเคียง `sorted(os.listdir())`
- ข้อความ error ของ file helpers รายงาน `errno N` แทน strerror ของ
  interp (ต่างจุดเดียวที่บันทึกไว้ใน AGENTS.md / docs)
- เทส `fs_helpers` (makedirs ซ้อน, append, exists จริง/ปลอม, ls สอง
  ชั้น) — x64 49 -> 50

### 15.30 port I/O ดิบใน kernel (v0.6.16)

`ioport_in(port, size)` / `ioport_out(port, value, size)` — ขั้นเดินสำคัญ
ของ driver ตัวจริง (ATA) เพราะ `asm()` มีแต่ฝั่ง native

- ภาษาไม่มี `asm` ใน `xkernel` จึงต้องมีทางออก: port I/O สดอยู่ใน
  runtime ฝั่ง freestanding หลัง `x_dict_helpers` เป็น `x_port_in` /
  `x_port_out` (size = 1/2/4 ไบต์; `in ax,dx` 16-bit zero-extend ให้เอง)
- ตัว builtin unbox argument เป็น machine word ก่อน (`sar 2`) — port
  number กับค่าเป็นเลขดิบ ไม่มี tag
- hosted build ปฏิเสธด้วย `builtin 'ioport_in' not in x64 subset` เหมือน
  syscall ตัวอื่นที่เป็นของ kernel
- assembler เพิ่ม `in_ax_dx`/`in_eax_dx`/`out_dx_ax`/`out_dx_eax`
- เทสใน kiotest: CMOS shadow RAM (0x70 index / 0x71 data) round-trip ได้
  ทั้ง 0x5A และ 0xA5 และความกว้าง 16/32-bit อ่านพอร์ตว่างได้ 0 —
  คือ driver จะคุยกับ register จริงได้

### 15.31 ATA driver (PIO) ตัวแรกของ OS (v0.6.17)

`kernel/kata.hs` — driver อ่าน/เขียน disk จริงตัวแรก เขียนด้วย `.hs`
ล้วน คุยกับ controller ผ่าน `ioport_in/out` จาก 15.30

- primary channel / master / LBA28: IDENTIFY (0xEC), READ (0x20),
  WRITE (0x30); PIO ทีละ word ผ่านพอร์ต 0x1F0 (ไม่ต้องมี DMA/IRQ)
- `present()` เช็ค IDENTIFY, `read_identify()` ดึง 256 word;
  `sectors()` อ่าน words 60-61, `model()` ถอดชื่อรุ่น (byte-swapped
  ในแต่ละ word, NUL ปนมา — compact แล้วค่อย `read_mem` เป็น Str)
- `read`/`write(lba, count, buf)` ตรวจ count 1..256, `select(lba>>24)`
  + `lba_setup` ก่อนสั่ง command แล้ว `wait_ready()` ตรวจ DRDY/ERR
- gotcha ที่เจอ: ค่าที่อ่านใน `unsafe:` เป็น block-local — ส่งออกด้วย
  `return` ผ่าน helper (`rd8`/`byte_at`/`put_byte`) แทนการ assign ตรง
- เทส `katatest` บูต QEMU พร้อมดิสก์ raw 1MB: identify, อ่าน sector 4
  ตรง pattern, เขียน sector 9 แล้วอ่านกลับเท่าเดิม, sector 10 ไม่เสียหาย
  — ต่อเข้า test_xkernel (274 -> 279)

### 15.32 Float ใน x64: IEEE-754 f64 โดยไม่มี libc (v0.6.18)

ช่องว่างหลักของ subset x64 ปิดแล้ว — `Float` เต็มรูปแบบทั้ง hosted
(`xbuild`) และ freestanding (`xkernel`) ด้วย `.hs`+machine code ล้วน

**การแทนค่า.** tag bit หมด (Int `01`, Bool `10`, Null `11`, heap `00`)
Float จึงเป็น heap object แบบเต็ม: kind `K_FLOAT = 5` เก็บ f64 bits ดิบ
(`[kind][f64]`) — ไม่มีทางเลือกอื่นที่ไม่ต้องแก้ทั้ง runtime

**คณิตศาสตร์.** `- * /` ใช้ SSE2 (`subsd`/`mulsd`/`divsd`) ส่วน `%` ใช้ x87
`fprem` + แก้ sign ให้เป็น `math.fmod` ตาม Python (`7.5 % 2.0 == 1.5`,
`-1.5 % 2.0 == 0.5`, `1.5 % -2.0 == -0.5`) ส่วน `/` และ `%` ด้วย 0.0 ให้
`division by zero` (catchable) เหมือน interp. Int ข้าง Float แปลงผ่าน
`cvtsi2sd`; Bool/Null ข้าง Float เป็น error (`cannot add Float and Bool`)

**เทียบ.** `ucomisd` — `0.0 == -0.0` true, `nan == nan` false, NaN ไม่มีทาง
`<`/`>` (คืน false ทั้ง `<=`/`>=` ด้วย แบบ IEEE). `1.0 == true` true เพราะ
Python ถือ Bool เป็นตัวเลข 0/1 ใน `==` แต่ *ไม่* ใน `<` (interp ทำแบบนั้น)

**`print`/`str`: shortest round-trip แบบไม่มี libc.** Python ใช้ dtoa
mode 0 = *shortest decimal ที่อยู่ในช่วง round-trip* ไม่ใช่ "ปัดเป็น
p หลักแล้วเอาที่สั้นที่สุด" — ต่างกันจริง เช่น
`6.290184345309701e-235` (ไม่ใช่ `...7005`) ขั้นตอน:

1. decompose เป็น `m x 2^e` แล้วขยายทศนิยมแบบ**ตรงเป๊ะ** บน bigint
   96 คำ (`m x 5^-e` ถ้า `e < 0`) เป็นสตริงตัวเลข
2. คำนวณขอบเขต round-trip ครั้งเดียว: midpoint กับ pattern เพื่อนบ้าน
   (`P-1`, `P+1`) เป็น `S x 2^(emin-1)` พร้อม flag ว่า endpoint inclusive
   ไหม (half-even ดูนิดท้ายของ pattern) — `Lp == 0` และ `Up == inf`
   มีทางพิเศษ
3. ลอง `p = 1..17`: เอา `T` = หลักตัวแรก `p` ตัว แล้วทดสอบ `T` กับ
   `T+1` ว่าอยู่ในช่วงไหม ถ้าอยู่ทั้งคู่เลือกข้างที่ใกล้กว่า (เทียบ
   `(2T+1)x10^K` กับ `2v` ด้วย bigint) — tie ไปทางหลักท้ายเลขคู่
4. พิมพ์แบบ Python: fixed ถ้า `-4 <= E10 <= 15` มิฉะนั้น scientific,
   `.0` เก็บไว้ให้เห็นว่าเป็น float, `inf`/`nan`/`-0.0` เป็นคำพิเศษ

**`float(str)`: parse ถูกต้องเสมอ.** เก็บ 100 หลักนัยสำคัญ + sticky bit
(`K` ผูกกับจำนวนหลักทศนิยม) แล้วเทียบแบบ cross-multiply บน bigint
(`dec_cmp`: `L/R == D_dec/D_dbl` เป๊ะ) จากนั้น binary search บน pattern
IEEE 63 รอบ จบด้วยการตัดสินที่ midpoint แบบ round-half-to-even
(เทียบ `2T+1` กับ `S x 2^emin`) — กับ sticky bit ทำให้ input ยาว
เกิน 100 หลักยังถูกต้อง ไม่ต้องพึ่ง FPU เลย (เลี่ยงบั๊ก subnormal/ties)

**เครื่องมือ.** assembler เพิ่ม SSE2/x87 (`cvtsi2sd`, `cvttsd2si`, `ucomisd`,
`addsd`..`divsd`, `movsd_*`, `fprem`, `fnstsw_ax`, `sahf`, `fstp_st1`, `shr_cl`)
+ `adc_*`/`mul_r`/`or_ri32`/`xor_ri32` และ bigint core 7 ตัว
(`bi_zero`/`bi_from_u64`/`bi_copy`/`bi_mul_small`/`bi_add_small`/
`bi_shl`/`bi_cmp`/`bi_divmod_small`) — ทุกตัว alias-safe (อ่านก่อนเขียนทีละ
word) เพราะทั้งสองทางเรียกแบบ in-place

**gotcha ที่เจอระหว่างทำ.**
- ค่าใน `unsafe:` เป็น block-local เหมือนเดิม; ที่ใหม่คือ `return` ใน
  generator ทำให้ `a.label(...)` ที่อยู่ถัดมาเป็น dead code →
  `undefined label` ต้อง `jmp` ไป end label แทน `return` ตรง ๆ
- สล็อต `[rbp-N]` ซ้ำกันสองตัวแปร = ค่าหายเงียบ (เจอ 4 ครั้ง:
  pointer กับ loop counter, `limit` กับ digit, `ecnt` ที่ PUTAL ทับ,
  `E10c` ที่ carry ดัน) — ดูดีก่อนอ่านค่าใน gdb
- buffer บน stack ต้อง `bi_zero` ก่อนใช้เสมอ ไม่งั้นผลขึ้นกับว่า stack
  page เคยถูกแตะหรือไม่ (เจอเป็น parse ผิดเฉพาะ subnormal)
- `x_dbl_parts` คืน `e = raw - 1075` (ไม่ใช่ `-1023`) เพราะ mantissa
  มี implicit leading 1 อยู่แล้ว
- midpoint คือ `S x 2^(emin-1)` ไม่ใช่ `x 2^emin` (S คือผลบวก) — ลืม
  `-1` ทำให้ทุก candidate เล็กไปหนึ่งเท่า
- ไม่มี libc แปลว่าไม่มี `snprintf("%.17g")` — ถ้าวันหนึ่งมี
  `extern:` ใน x64 การเพิ่ม Float จะถูก ง่ายกว่านี้มาก

**ผลการทดสอบ.** fuzz เทียบ `interp.py` (ซึ่งคือ CPython) กว่า 2500 ค่า
(สุ่มทั้งทศนิยมหลายรูปแบบ, bit pattern สุ่ม, 2^k/10^k ทุกขั้น, เพื่อนบ้าน
ของ subnormal/ศูนย์/max-double) — ตรงกันทุกตัว รวม `1e-08`, `5e-324`,
`1.7976931348623157e+308`; `int()`/`float()`/`str()` และ error messages
ตรงทุกเคส. เทส `tests/x64/float.hs` (x64 50 -> 51) และ
`kernel/kfloattest.hs` ที่บูต QEMU จริง (xkernel 279 -> 284)

### 15.33 JSON ใน x64: คอมไพล์ parser จากซอร์ส `.hs` เข้าไปใน image (v0.6.19)

`json_parse`/`json_str` เต็มรูปแบบทั้ง `xbuild` และ `xkernel`
(`json_load`/`json_save` hosted เท่านั้น เพราะต้องมี filesystem)

**วิธีที่เลือก.** ไม่เขียน JSON เป็น machine code ด้วยมือ แต่เขียนเป็น
hs จริงใน `runtime/json.hs` (ราว 430 บรรทัด) แล้วให้ x64gen **คอมไพล์ไฟล์นั้น
เข้าไปใน image** เป็นโมดูลส่วนตัวชื่อ `<json>` เฉพาะโปรแกรมที่เรียก
`json_*` — ตรวจด้วยการเดิน AST ก่อน `finalize` ถ้าเจอก็ `collect` + ออก
label `hsJF_*` แล้วสั่ง `emit_mod_init` เหมือน `import` ทุกอย่าง

- hook เดียวที่มีให้โมดูลนี้คือ `type_name(x)` ซึ่งคอมไพล์ตรงไปที่
  runtime `x_tname` (hs ไม่มี type introspection) โดย hook อยู่หลังเช็ก
  `mod["name"] == "<json>"` ผลคือถ้าผู้ใช้เขียน `import runtime.json`
  เอง (ทำได้ถ้า repo อยู่บน HSPATH) จะได้อีกสำเนาที่ไม่มี hook —
  ฟังก์ชันที่ต้องใช้ `type_name` จะคอมไพล์ไม่ผ่าน (`unknown variable
  'type_name'`) ไม่งั้นแค่ helper ที่ไม่ต้อง introspect
- entry point คืน 2-element List: `[null, value]` หรือ
  `["<message>", null]` แล้ว wrapper ที่ emit ใน `ev_call` เป็นคน
  `hs_raise_msg` ด้วย **บรรทัดของผู้เรียก** ข้อความ error จึงตรงกับ
  CPython ที่ interp ใช้ทุกตัว: `Expecting value`, `Extra data`,
  `Expecting ',' delimiter`, `Illegal trailing comma before end of array`,
  `Unterminated string starting at`, ... รวมถึง
  `json_str failed: Out of range float values are not JSON compliant: inf`
  และ `not JSON-serializable: Builtin`
- parser/encoder เขียนแบบ byte-oriented (x64 Str คือ buffer UTF-8) จึง
  ต้องอ่านค่า byte เป็น Int — ทำด้วย `byte_at()` = `as_ptr` + `load8`

**สิ่งที่เจอระหว่างทำ (สำคัญ).**
- **`and`/`or` ฝั่ง x64 ไม่ short-circuit** ทั้ง interp และ native
  short-circuit แต่ x64 รันทั้งสองข้าง → `while i < len(s) and s[i] == "x"`
  พังทันที (`index out of range`) แก้โดยเขียน bound check เป็นการเรียก
  เดี่ยว (`js_at(s, i, n)` คืน -1 เมื่อเลยปลาย) แล้วเทียบ
- **hs ไม่มี `chr()`** แต่ encoder ต้องปั่น byte ดิบ (UTF-8 ส่วนที่
  escape ไม่ได้) วิธีเดียวที่ subset มีคือ `alloc` + `store8` + `read_mem`
  (`js_chr`) — ช้ากว่ามากแต่ถูก
- **`append()` คืน Null** (เหมือน interp) ไม่ใช่คืน list → ต้องแก้ list
  ใน place ไม่ใช่ `x = append(x, y)`
- **register ที่เก็บค่าข้าม `call` ได้ไม่ได้** — ตอนแรกเก็บข้อความ error
  ไว้ใน rcx แล้วเรียก `x_str_at` เพื่อสร้าง prefix `"json_parse failed: "`
  rcx ถูก clobber ทิ้ง เปลี่ยนเป็นเก็บบน stack
- **x64 ไม่มี mutual recursion** และ resolve ชื่อ module-level แบบ static
  → ต้องรวม array/object parsing ไว้ใน `js_value` ตัวเดียวที่เรียกตัวเอง
  ได้ (คำนวณไว้ใน `runtime/json.hs` เพราะไม่มี `int()`/`ord()` ให้แยกว่า
  Int กับ Float — ใช้ `str()` + first char หรือ `len()` + first char แยกแทน)
- **list ใน x64 คือ `[kind][len][cap][buf]`** element อยู่ใน buf ไม่ใช่
  inline → wrapper ต้องอ่าน `[[rax+24]+8]` ไม่ใช่ `[rax+16]`
- `finalize()` เดิมใช้ module scope ของ `<main>` เป็นขอบเขตการหา
  capture ทำให้ชื่อ module-level ของโมดูลอื่นถูกมองเป็น capture (แล้ว
  อ่าน global ที่ยังไม่ assign = `unknown variable`) แก้เป็นหยุดที่
  module scope ของตัวเอง (`p is p._mod.get("scope")`)
- Python `return` ในตัว emit ทำให้ `a.label(...)` ที่อยู่ถัดมาเป็น dead
  code (undefined label) — json_save เลยต้อง emit ทั้งก้อน inline ไม่ใช่
  `jmp` ไป label ท้ายฟังก์ชัน
- **เทสต์ x64 ไม่ได้เตือนเรื่อง stack** — หลักฐานคือ `gdb` ดู
  `mov 0x8(%rdi),%rax` ที่ rdi = 0 แล้วไล่กลับด้าน call chain

**บั๊กที่เจอใน x64 ระหว่างทำงานนี้ (แก้แล้ว).** `int(x)` เมื่อ `x` เป็น Int
ทาง passthrough ไม่ `pop` ค่าที่ push ไว้เพื่อทำ message
→ ทิ้งสแต็คค้าง 8 ไบต์ ทำให้ `s[int(n)]` อ่าน operand ผิดตัว
(`cannot index Int`) และการกิน stack ใน expression ที่ซับซ้อน ก้อนนี้
เพิ่มเทสต์ `tests/x64/float.hs` (บรรทัดท้าย) กันซ้ำ

**ผลตรวจ.** differential test เทียบ interp (ซึ่งคือ CPython) 44 เคส encode
+ 79 เคส decode — ตรงกันทุกตัวทั้ง stdout, stderr และ exit code
รวมข้อความ error และเลขบรรทัด เทส `tests/x64/json.hs` (x64 51 -> 52)
และ `kernel/kjsontest.hs` ที่บูต QEMU จริง 18 assertion + 4 error
(xkernel 284 -> 291)

### 15.34 เลขทศนิยมนับยกกำลังได้ + native print float แบบ shortest (v0.6.20)

คำถามว่า "ภาษาครบ 100% ไหม" เปิดช่องโหว่สองตัวที่ไม่ใช่ฟีเจอร์ที่สเปก
เขียนไว้ แต่เป็นบั๊กจริงที่ต้องแก้

**1. `1.5e3` ไม่ใช่เลขทศนิยม.** lexer เดิมมีแต่
`[0-9]+\.[0-9]*|\.[0-9]+` เลยตัด `1.5e3` เป็น `1.5` แล้วเหลือ
`e3` ไว้ให้ตายด้วย `unknown variable 'e3'` — ภาษาที่ indent เหมือน
Python แต่เขียนเลขยกกำลังไม่ได้ ตอนนี้ regex เป็น
`[0-9]+\.[0-9]*([eE][+-]?[0-9]+)?|\.[0-9]+([eE][+-]?[0-9]+)?|[0-9]+[eE][+-]?[0-9]+`
และเก็บ `raw` ไว้ด้วยเพื่อให้ `hs fmt` คืนรูปเดิม (`1.5e3` ไม่กลายเป็น
`1500.0`) — `0xFF` ก็เก็บแบบเดียวกันอยู่แล้ว

**2. native print Float ไม่ตรง interp 48% ของค่า.** `v_disp` ใน
`native/rt.c` ใช้ `%.17g` ตรง ๆ ซึ่งพิมพ์ 17 หลักนัยสำหรับทุกค่าที่ไม่
แน่นอน: `print 0.1` ได้ `0.10000000000000001` แต่ interp ได้ `0.1`
fuzz 674 ค่า match แค่ 322 — **บั๊กนี้มีมาตั้งแต่ Float เข้ามาใน native
(ไม่ใช่ของรอบนี้) และไม่เคยถูกจับ เพราะไม่มี test ไหน print float
ที่ไม่แน่นอน** แก้ด้วย `fmt_repr()` ที่หา significant digits สั้นที่สุด
(ไล่ 1..17 แล้วเช็คว่า `strtod` อ่านกลับได้ค่าเดิม) แล้วจัดรูปแบบตาม
CPython: fixed ตอน 1e-4 <= |x| < 1e16, มี `.0` ตอนลงตัว, เลขชี้กำลัง
อย่างน้อย 2 หลัก → ผ่าน 2021 ค่าใน 3 seed ที่ fuzz มา ตอนนี้ 100%

**3. บั๊ก x64 ที่เจอระหว่างทำ: `float("1e309")` ได้ nan.** ค้นพบตอน
fuzz float หลังแก้ข้อ 2 (seed 77) — `nearest_double()` ไบนารีเซิร์ชค่า
IEEE pattern โดยตั้ง `hi = inf` แล้วเดิน `lo = mid + 1` 63 รอบ พอ `lo`
ชน `hi` ที่เป็น pattern ของ inf พอดี ขั้นถัดไปก็เดินข้ามไปเป็น NaN
(`0x7FF0000000000001`) แล้วคืน nan กลับออกไป แก้ด้วย clamp
`lo = min(mid + 1, hi)` → ทุกอย่างที่เกิน max double กลายเป็น `inf`
ตาม Python

**4. native ต้องมีวิธีพิมพ์ `inf`/`nan` ที่ literal.** `repr(float('inf'))`
ให้ `inf` ซึ่งเป็น identifier ไม่ใช่ constant ใน C (gcc error) เลยเพิ่ม
`hs_f64raw(uint64_t)` ใน `rt.c` แล้ว emit เป็น bit pattern ตรง ๆ
(`v_float(hs_f64raw(0x7ff0000000000000ULL))`) แทนการผูก `math.h`

หลักฐาน: `tests/floatlit.hs` (interp 42 / native 43), `tests/x64/float.hs`
ยาวขึ้น, `tests/test.py` 41 -> 42, `tests/test_native.py` 42 -> 43

### 15.35 IR กลาง: CFG ที่ backend ทุกตัวต้องกินแทน AST (v0.6.21)

ก้าวแรกของแผน self-hosting (`docs/superpowers/plans/2026-10-08-ir-backend.md`):
`ir.py` สร้าง flat CFG จาก AST ของ `interp` — temp นิพจน์เป็น SSA บริสุทธิ์
(`%1`, `%2`, ...), ตัวแปรซอร์สอยู่ในเฟรม (`stvar`/`load`), โฟลว์เป็นบล็อก
ชัด (`jmp`/`br`/`ret`) พร้อม verifier (label ซ้ำ, โดดข้ามบล็อกที่ไม่มี,
temp ไม่ได้นิยาม, phi ผิด) กับ reference interpreter ที่ต้องตรง `interp`
ทุกไบต์ทั้ง stdout/stderr/rc

การตัดสินใจสำคัญ: `and`/`or` lower เป็น branch+phi (short-circuit เหมือน
interp) — นี่คือจุดที่ x64 ปัจจุบันทำผิด (รันทั้งสองข้าง) และ backend x64
ต้องทำ branch จริงตอนย้ายมากิน IR (Task 4). ตัวแปรไม่ทำ mem2reg ตั้งแต่
ต้น (รอ Task 3) เพื่อให้ closure/forward-ref/path-dependent definedness
ถูกโดย construction — ฟัซซ์ differential 590 โปรแกรมสุ่มตรงกันหมด
(ที่เหลือคือ infinite loop ที่ฟัซเซอร์สร้างเอง แฮงก์เหมือนกันทั้งสองฝั่ง)

divergence ที่ตั้งใจและจดไว้ใน `ir.py`: `break`/`continue` นอก loop กับ
`return` นอกฟังก์ชันเป็น `error:` สะอาด ส่วน interp ปล่อย exception
หลุดเป็น traceback — จะ match traceback ตรง ๆ ไม่ได้เพราะผูกกับ layout
ไฟล์ของ `interp.py` เอง

หลักฐาน: `ir.py`, `tests/test_ir.py` (16 differential + 4 verifier/builder
+ dump + unsupported), `tests/run_all.py` มี suite ที่ 9, `docs/errors.md`
มี section `ir.py` (ผ่าน `scripts/gen_errors.py` ที่รู้จัก `ir.py` แล้ว)

### 15.36 Container + `for` ใน IR (v0.6.22)

Task 2 ของแผน IR: `list`/`dict` literal, `index`/`slice`, `setindex`,
`for` (desugar เป็น len/index/while บนสล็อตเฟรมส่วนตัว `$itN`/`$iN`
ชื่อชนกับโค้ดผู้ใช้ไม่ได้เพราะ `$` เขียนในซอร์สไม่ได้) พร้อม builtin
เพิ่ม `range`/`append` (reuse ฟังก์ชันเดียวกับ interp ข้อความจึงตรง
โดย construction)

บั๊กที่ differential เจอ: `continue` ใน `for` โดดข้ามขั้น increment
(แขวนทั้งลูป) — แก้ด้วย incr block กลาง: body/break/continue ที่ตกผ่าน
เข้าบล็อกเพิ่มค่าก่อนกลับ header ส่วน `while` ใช้ header ตรงเหมือนเดิม
(แยกด้วย `incr: None`)

หลักฐาน: `tests/test_ir.py` 23 -> 47 (เคส container/`for` 16 +
`forcontinue` + corpus differential บน `tests/*.hs` ทั้งคลัง: 9 ผ่าน,
33 ข้ามนอก subset อย่างนับแยก), ฟัซซ์สุ่มเพิ่ม 292 โปรแกรมตรงกันหมด
(รวมสองรอบ 882 เคส, timeout ที่เหลือคือ infinite loop แท้ในซอร์สที่
แฮงก์เหมือนกันทั้งสองฝั่ง)

### 15.37 Dominance verifier + รูปแบบ text ของ IR + `hs.py ir` (v0.6.23)

Task 3 ของแผน IR: verifier ตรวจ def-dominates-use จริง (dominator แบบ
iterative dataflow, phi arm ต้อง dominate บล็อกต้นทางของ edge; บล็อกที่
ไปไม่ถึงได้รับยกเว้นแต่ยังต้องมี terminator ถูกทรง) พร้อมรูปแบบ text
มาตรฐาน: `hs.py ir prog.hs` พิมพ์ CFG (`func key(params):`, `label:`,
`@line` ท้ายทุกบรรทัด, `-` แทน None, string escape `\uXXXX` รวม
surrogate pair) และ `parse_module` อ่านกลับ — round-trip ทั้ง text
เท่ากันและการรันเท่ากัน ครอบทุกเคสใน `test_ir.py` รวมสตริงโหด
(quote/backslash/NUL/ไทย/astral/ลงท้ายด้วย ` @3`)

ของแถม: `_jerr` ใน `hs.py` ถูกเรียกแต่ไม่เคยนิยาม — path `--json`
ตอน error พังด้วย NameError มาตลอด แก้ 6 บรรทัดให้ตรง contract
`{"file","line","message"}` ที่เอกสารสัญญาไว้ พร้อม regression test
(`hs-ir --json`)

หลักฐาน: `tests/test_ir.py` 47 -> 83 (dominance unit + round-trip 33 +
`hs.py ir` dump/--json), `docs/errors.md` งอก section ข้อความ IR

### 15.38 IR -> x64: backend ที่สองกิน IR โดยตรง (v0.6.24, Task 4 part 1)

`irx64.py` เป็น Gen subclass ที่ reuse runtime ทั้งก้อนของ x64gen
(value model, heap, builtins, error) กับ leaf emitter
(emit_add/compares/arith/bitop/un/print/call/func-construct) — สิ่งที่
เขียนใหม่มีแค่ driving layer: temp/ชื่อ -> frame slot, IR block ->
label, phi -> store บน edge, call ผ่าน protocol เดียวกันทั้ง user func
และ builtin values, `hs_main`/`_start`/link ต่อท้ายแบบเดียวกับ
build_image

กับดักที่เจอ: builtin บางตัวใน x64 ไม่มี value form (`float`,
file helpers) — `load float` แล้ว call ผ่าน value protocol จะ segfault
(r15 ขยะ) เพราะ num arms ของ ev_call เป็น inline emitter
แก้ด้วย provenance: temp จาก `load` ของ inline-only builtin ที่ feed
เฉพาะ call-fn จะได้ dummy (inline path ทิ้งค่าอยู่แล้ว) นอกนั้น error
`is not a value` เหมือนเดิม; shadowing (`float = 5` ของผู้ใช้) ยังถูก
เพราะ resolve ตาม scope chain ก่อนเสมอ

หลักฐาน: `tests/test_irx64.py` เทียบ ELF ชน ELF (IR path vs AST path)
9/9; ที่เหลือข้ามอย่างนับแยก (containers = slice ต่อไป; try/import/
unsafe = งานหลัง; ref ปฏิเสธเองอีก 9)

### 15.39 irx64 part 2: containers + เรียก builtin ตรงแบบ inline (v0.6.25)

- Container ops ครบ: build_list/dict (stack + x_list_new/x_dict_new),
  index/slice/setindex (transliterate ev_index/ev_slice/ex_setindex),
  iterseq (List/Str ผ่าน, Dict เป็น list ของ keys ผ่านลูป machine code
  ไม่มี call ข้างใน) — `for` ทำงานบน IR path แล้ว
- เรียก builtin ตรงต้อง inline: ฟัซซ์จับได้ว่า `len` ของ Int รายงาน
  `len of Int` ไม่มีเลขบรรทัดบน IR path (stub อบ line 0 ไว้) ขณะที่
  AST path มี — เพราะ ev_call มี inline arm แยกจาก value protocol
  แก้ด้วย provenance: temp จาก `load` ของ builtin ใน INLINE_DIRECT
  ({float,len,str,int,range,append}) ที่ feed เฉพาะ call-fn และไม่ถูก
  shadow จะเรียก inline emitter (error ตรงบรรทัด); first-class use
  ยังผ่าน stub เหมือนเดิม
- `for k in dict`: IR ทำ keys-snapshot เหมือน interp ส่วน x64gen เดิม
  เดิน buf สด — IR path ถูกกว่าเดิมตรงนี้ (harness รับเมื่อตรงฝั่งใดฝั่งหนึ่ง)

หลักฐาน: `tests/test_irx64.py` 9 -> 13 (for/func/types/t_strfun),
ฟัซซ์ ELF-ชน-ELF 240 เคสตรงกันหมด

### 15.40 import ครบ end-to-end บน IR (v0.6.26, Task 4 part 3)

- `ir.py`: builder รับ `import`/`attr`/`setattr`, interpreter มี module
  registry จริง (file resolve แบบ interp, dotted + shell package,
  circular error, `in module` wrap, init รันครั้งเดียว, attr read/write,
  `print mod` เป็น `<module name>`) — `tests/t_import.hs` ตรง interp
  ทุกไบต์
- `irx64.py`: resolve ตอน build (parent-first + shell + circular),
  merge funcs ด้วย dotted prefix, global แยกต่อ module, init guard
  แบบ hsM_init, attr resolve แบบ static (submodule = phantom temp
  ที่ value-use แล้ว error ชัด), `print mod` ตรง, copies ของ module
  (`x = mod`) เป็นช่องโหว่ที่จดไว้
- กับดัก: alias-load ต้องข้าม emission เมื่อทุก use เป็น chain
  (ไม่งั้น UNBOUND check ลั่นก่อน attr จะ resolve), attr ซ้อน
  (`std.str.trim`) ต้องรับ mval ไม่ใช่แค่ mod

หลักฐาน: `test_ir.py` 83 -> 86, `test_irx64.py` 13 -> 18
(t_import/t_pkg/t_std ผ่าน; t_heap ยังติด unsafe ถูกต้องแล้ว)

### 15.41 try/except/finally/raise บน IR ทั้งสองชั้น (v0.6.27, Task 4 part 4)

- `ir.py`: ops ใหม่ `try_push/try_pop/exc_str/exc_pop/unbind/reraise`
  กับ terminator `raise`; builder inline finally บนทุกทางออกฉับพลัน
  (return/break/continue พร้อม depth rule แบบ x64gen ผ่าน trystack),
  handler shape ครบ (guard ซ้อนสำหรับ error ใน handler + finally,
  save/restore ตาม shadow analysis ทั้งฟังก์ชัน); interpreter ใช้
  Python exception + handler stack แยกเฟรม (_Jump ข้าม _call)
- `irx64.py`: transliterate ตรงจาก ex_try (hs_try_push0/pop,
  hs_exc_str/pop, hs_reraise, hs_raise_raw/Msg) พร้อม exc runtime +
  data เมื่อมี try; bare raise ตรวจตอน build เหมือน x64gen
- ฟัซซ์จับได้อีกแล้ว: `len` เสีย line (แก้ด้วย inline ไปแล้วรอบก่อน),
  รอบนี้ `try_push` คู่กับ `unbind` ระดับ module ที่ลืม (slot ไม่มี
  เพราะ entry-stvar เป็น global)

หลักฐาน: `test_ir.py` 86 -> 108 (10 เคส try + corpus t_try/t_finally/
t_closure/t_circ ผ่าน), `test_irx64.py` 18 -> 22, ฟัซซ์ try 350 เคส
บวก x64-diff 370 เคสตรงกันหมด

### 15.42 `unsafe:` บน IR ทั้งสองชั้น + xbuild สับไป IR (v0.6.28, Task 4 part 5 + switchover)

- `ir.py`: static world เป็น ops จริง ไม่ใช่ตัวแปร Python ซ่อนไว้
  - ค่าคงที่/ดึงตัวแปร/เอาเครื่องหมาย: `sconst`, `sload`, `sraw`, `snz`,
    `sbin`, `sun`, `sfield`, `sderef`, `ssizeof`, `scall`
  - พิมพ์/อ่านเขียน/ผูก: `sdecl`, `sset`, `sstore`, `sfstore`, `box`,
    `svarptr` (as_ptr/as_int ของตัวแปรตรง — x64gen ไม่ unbox ก่อนแต่
    ให้ dispatch ที่ tag เป็นตัวตัดสิน โค้ดเดียวกับ x64gen)
  - error ที่ผูกกับ shape (`str`/`float` literal, collections, attr, slice,
    call ผลลัพธ์) ย้ายไปเป็น `serr` runtime พร้อมข้อความสองฝั่ง (`imsg`
    ของ interp / `xmsg` ของ x64) เพื่อให้ stdout ตรงกันแม้ตอน error
    ตำแหน่งจะต่างกัน (build ของ x64gen vs runtime ของ interp)
  - interpreter: `UnsafeVal` ตาม `interp.sev*` เป๊ะ — I64/U64/Ptr/LIT
    ห้ามผสม, ชี้เป็น `Ptr` ไม่ได้, `U64` ใหญ่เกิน Int box ไม่ได้; หน่วยความจำ
    จำลอง 1MB (`_us_alloc/_us_load/_us_store`) + `read_mem` ผูกกับ image นั้น
  - ตัวแปรที่ถูก `sdecl` แล้วอ่านจาก safe code ต้อง coerce กลับ
    (`dset`) ไม่ใช่ทับด้วยค่า dynamic ตรงๆ
- `irx64.py`: lowering ตาม `sev*`/`ex_unsafe` ของ x64gen แบบคำต่อคำ
  (raw word ไม่มี tag check, `/` ตัดทิ้ง, `print` ใช้ `print_int`, `fstore`
  ดัน address ก่อนโหลดค่า, `as_ptr` dispatch tag), `struct` ชนิดของ pointer
  มาจาก `Ptr:X` declaration + propagation `+`/`-` + field ซ้อน (`_struct_of`),
  ชื่อซ้ำใน scope เดียวกัน fail ตอน build, `serr`/`ssizeof` ใช้ข้อความฝั่ง x64
- JSON บน IR: `runtime/json.hs` คอมไพล์เป็น module ปกติ (`<json>`) แล้ว
  `json_*` เรียกผ่าน `call_js_entry` + `js_finish` ชุดเดิม, hook เดียวคือ
  `type_name` ในโมดูลนั้น (ตรงกับ AST path เดิม)
- **Switchover**: `x64gen.build_x64` เดิน parse → IR → verify → GenIR แล้ว;
  path เก่าย้ายไปชื่อ `build_x64_ast` ใช้เป็น reference ของ `test_irx64.py`
  และยังเป็นทางที่ `xkernel` (freestanding) ใช้อยู่
- ฟัซซ์จับได้: nested `and`/`or` ทำ phi arm ชี้ non-predecessor
  (ต้องอ่าน label ปลายทางจริงหลัง evaluate), `sraw` ปนเข้า `sbin`,
  `ssizeof` ทำให้ struct ไม่รู้จักตอน build, module alias copy
  (`x = mod`) เคยตายเพราะ alias เกิดตอน emit แต่ dead-load คำนวณตอน plan

หลักฐาน: `test_x64.py` 52/52 ผ่านบน IR path, `test_irx64.py` 22 -> 35
(เทียบ ELF ชน ELF กับ path เก่า, เคสที่ต่างกันขึ้น flag `!!` พร้อมบันทึกว่า
IR path ตรงกว่า เช่น segfault ของ `tests/ufunc.hs` ที่ path เก่าพัง),
`test_ir.py` 108 -> 134, ฟัซซ์ 480 เคส (IR + x64) ตรงกันหมด

### 15.43 `hs.py xkernel` กลับมาทำงาน + เคส QEMU ที่ค้างผ่านหมด (v0.6.29)

- บั๊กจริงที่หลุดมาตั้งแต่ v0.6.23: ตอนแทรก branch `ir` ใน `main()` ของ `hs.py`
  บรรทัด `if argv[1] == "xkernel":` หายไปติดกับ branch `xbuild` ทำให้
  `hs.py xkernel` ไหลไปเข้า native backend (gcc) แล้วพังด้วย TypeError
  — ชุดเทสไม่จับเพราะเรียก `x64gen.build_xkernel` ตรง ๆ ไม่ได้ผ่าน CLI
- เพิ่ม regression 3 เคสใน `test_x64.py`: สแกน AST ของ `hs.py` ยืนยันว่า
  subcommand แต่ละตัวมี branch นึงและไม่มี branch ซ้ำ (`run` เป็น
  fall-through ตั้งใจ ไม่มี branch) + สร้าง ELF freestanding จริงผ่าน CLI
- เคส QEMU ที่ค้างมานาน (`kio` EXC 14 ×3, `kush` sendkey) ผ่านหมดในรอบ
  เต็ม: `test_xkernel.py` 291/291 — เคยเป็นปัญหา environment ของ QEMU
  (รันเดี่ยว ๆ ผ่านตั้งแต่ก่อน) ไม่เกี่ยวกับงาน IR

### 15.44 บั๊กจริง 5 ข้อบน x64 ที่ชุดเทสเดิมมองไม่เห็น (v0.6.30)

เปิด `xbuild` ไปทาง IR แล้วต้องพิสูจน์ว่า path ใหม่ยังตรงทุกภาษา ไม่ใช่แค่ผ่าน
`tests/x64/` — เพิ่มการเดินคอร์ปัส `tests/*.hs` ทั้งหมดผ่าน IR path แล้วเทียบผลรันกับ
`interp.py` (build error ที่ `.fail` ตรงก็ถือว่าผ่าน, ข้างนอก subset ขึ้น SKIP,
ต่างที่เอกสารรับรองไว้แล้วขึ้นเป็น "known divergence" ไม่ใช่ SKIP เงียบ ๆ) ผลคือ
เจอบั๊กที่ไม่เคยมีเทสต์ครอบ:

1. **`Int / Int` คืน Int** ไม่ใช่ Float — ผิดสัญญาภาษา (`7 / 2 is 3.5`); x64 เดิม
   ตกไปทาง `idiv` ทั้งที่มี float path อยู่แล้ว แก้ด้วย `cvtsi2sd` + `divsd`
   (ปัดเป็น half-to-even ตรงกับ `float(int)` ของ interp) ทั้ง safe path
   ของทั้งสอง backend; `unsafe:` คง truncate แบบ C ตามที่เคยกำหนด
2. **`%` ตาม C ไม่ตาม Python** — `-7 % 3` ได้ `-1` แทน `2` (เติม divisor
   เมื่อเศษกับตัวหารคนละเครื่องหมาย)
3. **nested def ที่เรียกตัวเองพัง** — closure เก็บ capture ก่อน `var_set` ผูกชื่อ
   ตัวเอง ทำให้อ่านได้แต่ UNBOUND; แก้ด้วยการอ่าน capture **หลัง** `var_set`
   (AST path) และให้ self-capture ชี้ object ที่กำลังสร้าง (IR path)
4. **`json_load` ส่ง File ที่ปิดแล้วให้ decoder** — ดัน slot ผิดตำแหน่ง
   (`add $8` ก่อน `pop`) ไม่มีเทสต์ครอบเลย; json_parse/json_save ผ่านมาตลอด
   ทำให้เห็นแค่ตอนรันคอร์ปัสเต็ม
5. **`x_str_cmp` ตัดสินด้วยความยาวอย่างเดียว** — `"ab" < "b"` ได้ false
   ทำให้ `ls` **กลับดับ**รายการ และ dict lookup ของ key ที่หนึ่งเป็น prefix
   ของอีกอันพัง; แก้ให้ scan ไบต์ร่วมก่อน แล้วค่อยตัดสินด้วยความยาว
   (พร้อมแก้ `x_list_sort_str` ที่ใช้ `rcx` ซึ่ง `x_str_cmp` ทำลายทิ้งเป็น
   swap index ผิด)

ผลข้างเคียงที่ต้องแก้ตาม: `kernel/kmb|kpage|kpmm.hs` ใช้ `/` ในโค้ด safe
เพื่อหารจำนวนเต็มมานาน (พึ่งบั๊กเดิม) — เปลี่ยนเป็น `int(x / y)`; freestanding
`1 / 0` ยังคงเป็น `#DE` เพราะ SSE divide ไม่ trap (เพิ่ม `idiv` ตัวดักไว้ให้
ตัวเอง); `tests/x64/fib.expected` เดิมจด `20 / 4` เป็น `5` ตามบั๊ก — แก้เป็น `5.0`
ตาม interp; `test_xkernel.py` ให้ session B เวลา 30 วินาที (เดิม 20 วินาที
คือเส้นชั่วชาต่อเมื่อ image ใหญ่ขึ้น)

หลักฐาน: `test_x64.py` 52 -> 97 (เพิ่มการเดินคอร์ปัสทั้งหมด + 3 CLI),
`test.py` 42 -> 48, `test_native.py` 43 -> 49, `test_ir.py` 134 -> 138,
`test_irx64.py` 35 -> 41, `test_xkernel.py` 291/291

## ขีดจำกัดของ x64 backend และการเลือก backend ของ `hs run`

- `hs run` ลอง x64 ก่อน (build ~0.1s ไม่ใช้ gcc) ถ้าโปรแกรมอยู่นอก subset
  หรือมี Int literal เกิน 62-bit จะ fallback ไป native (gcc) หรือ interp เอง
- **Int บน x64 กว้าง 62-bit** (-2^61 .. 2^61-1) แต่ interp เป็น Python int
  (ไม่จำกัด) และ native เป็น 64-bit ค่าที่ล้น 62-bit จะ **ไม่ถูกตัดเงียบ ๆ**:
  build hosted จะ trap ด้วย `error: Int outside the 62-bit range ...` exit 97
  (บวก/ลบ/คูณ/shift/ประกอบ tag) ถ้ายังไม่มี output/side effect `hs run`
  จะรันซ้ำด้วย backend ที่ช้ากว่าให้เอง ไม่งั้นพิมพ์ error ชัดเจน + hint
- ค่าใน `unsafe:` เป็น machine word ดิบ ไม่ตรวจ 62-bit; kernel (freestanding)
  ยังตัดเป็น 62-bit เหมือนเดิม
- `true == 1` เป็น `true` ทุก backend (เหมือน Python/interp)
- บังคับ backend: `HS_BACKEND=auto|x64|native|interp` หรือ `hs.py run prog.hs --backend X`

### Default args (parse-time desugar)

- `def f(a, b=1 + 2):` ค่า default ต้องอยู่หลัง param ที่ไม่มี default เท่านั้น
  (ผิด = error ตอน parse)
- เรียก `f(x)` (มี f เป็น `def` ระดับบนที่ชื่อไม่ซ้ำ) ตัว parser เติม argument ท้ายที่ขาด
  ด้วยสำเนาของ expression default **ทุกครั้งที่เรียก** (ต่างจาก Python ที่คำนวณตอน def;
  `[]` ได้ list ใหม่ทุกครั้ง) backend ทุกตัวจึงเห็นแต่การเรียกเต็ม arity
- ยังไม่รองรับ: method ใน class (error ตอน parse), เรียกผ่านตัวแปรอื่น/lambda
  (จะได้ error arity ตามปกติ), `selfhost/cc.hs` (reject)
- ทดสอบ: `tests/t_defaults.hs` (ทุก backend), `tests/err_defaults.hs`

### Runtime allocation: strings
String length and contents are unchanged. x64 string copy/concatenation
allocates the 16-byte object header plus payload, rounded up to 16 bytes.
No extra spare block is required: strings are immutable and all readers use
the stored byte length. C-string conversion keeps its separate terminator.

### Unsafe C ABI entry invocation (Linux x86-64)
`unsafe: I64 result = call0(Ptr)` invokes a non-null address using the C ABI
with no arguments and an I64 return. The caller owns executable memory, ABI
correctness and lifetime. The interpreter permits only foreign pointers
when extern has enabled foreign memory; simulated arena pointers are
rejected. Null is a catchable error. Invalid non-null addresses can crash,
as with other unsafe memory operations. This does not call hs functions
with their internal ABI and is unavailable in freestanding kernel mode.
### Executable memory groundwork (Linux x86-64)
`selfhost/jitmem.hs` owns a page-rounded mapping for nonempty byte lists of
at most 16 MiB. `publish` validates before mapping, copies into RW (not X)
memory and changes the whole mapping to RX (not W). Failure releases the
mapping. `release` unmaps it once and clears its handle; double release is
an error. The caller must not use an address after release or while it is
being released. This internal module does not call generated code, change
`hs run`, provide first-call compilation, or constitute a JIT. It currently
uses the system C ABI for mmap/mprotect/munmap, not a libc-free runtime.

`jitmem.publish_sections(code, data, relocate)` additionally reserves adjacent
page-aligned code/data sections. A relocation callback receives both bases
before copying; its output must be a byte list of the original code length.
Only code becomes RX; data remains RW and never executable. The entire
reservation is released together, including on callback failure.
`selfhost/jitimage.hs` adapts the current hs assembler state to these bases,
checking undefined labels and signed rel32 reach before resolving. Multiple
images have independent data and lifetime. This is relocation groundwork,
not whole-program entry execution or ELF loading.

### Experimental eager in-process compiler execution
`selfhost/be/jit_run.hs SOURCE [args...]` is a Linux x86-64 experiment. Build
the driver with the native hs compiler, then it parses/normalizes source,
verifies optimized IR, emits code in hs, relocates into RX code/RW data and
invokes the generated entry in the same native process. It does not write
or exec a target ELF. The sections-only emitter finalizes code/data without packing an ELF. The driver forwards argv and reads the
initial process environment from /proc/self/environ. Explicit shared-library paths/sonames are loaded by the host libc loader and
extern GOT slots are bound before publication. Bare short library names remain
outside the native driver subset.

This is eager whole-program in-memory compilation, not compile-on-first-call
or a tiering JIT. The generated _start exits the process, so control never
returns to the compiler driver; final memory cleanup belongs to the OS.
Runtime output/errors match the reference on the differential cases;
compile-time diagnostics are still experimental, not a parity claim. The
normal hs run command and its fallback/cache behavior are unchanged.

`scripts/run-jit-native.sh SOURCE [args...]` packages the experiment with a
verified seed, an isolated temporary native driver and cleanup. It needs
no Python/gcc at runtime, but builds the driver each time. This extra build
time is excluded from any already-built-driver startup measurements.

### Formatter preservation of NUL
The canonical spelling of an embedded NUL byte is `\0`, the string escape
accepted by the parser. Formatting a string must preserve its contents and
must not rewrite NUL as an unsupported Unicode escape. The gcc-native
backend emits literal byte lengths explicitly, preserving embedded NUL.

### Mixed C ABI register arguments
Hosted x64 extern calls independently use up to six integer/pointer/string
registers and eight F64 registers under the SysV x86-64 ABI. A mixed
signature can therefore have up to fourteen register arguments. Declaration
order is preserved across the independent register banks. Arguments beyond either bank are passed in declaration order on the
16-byte-aligned caller stack. At most 32 fixed arguments are supported. This
does not add variadic calls, callbacks or struct-by-value.

An extern U64 argument rejects a negative safe Int before entering C on all
hosted backends. This is a catchable type-conversion error, not a cast to
a large unsigned value. Bool and non-Int arguments remain rejected.

### Eager in-process extern binding
The Linux x86-64 eager driver may request sections with an unresolved extern
GOT, load declared prebuilt shared libraries with dlopen and bind all symbols
before executable publication. A missing library or symbol is a compilation
failure: target code must not run. Handles remain live for the target process
lifetime. The ordinary sections API still rejects externs unless explicitly
requested. This uses the host libc dynamic loader, not a self-written loader,
and adds no callbacks, variadics, tiering or compile-on-first-call.

Each eager extern symbol binds against its declared library handle, not an
undifferentiated process-global search. Relative library paths are based on
the source directory. Duplicate C symbol names with different library owners
are rejected by the x64 backend because its GOT is keyed by symbol name. The
name fflush is reserved to libc for runtime output ordering.

### Explicitly typed C variadic calls
An extern parameter list may contain one `...` marker after at least one
fixed parameter and before at least one typed variadic parameter. Example:
`I64 printf(Str format, ..., I64 value, F64 fraction)`. The complete hs call
still has exactly the declared number of arguments. The marker changes the
C prototype and ABI classification, not hs arity or argument conversion.
I64/U64/F64/Str/Ptr are already promoted C ABI types; no automatic type
inference, narrow integers, float32 or untyped hs varargs are added. Format
strings remain the caller's responsibility, as with any unsafe C contract.

### Relocatable native directory bundle
`scripts/build-native-bundle.sh OUTPUT` creates a new Linux x86-64 directory
with the pinned compiler, an ahead-built eager driver, hs compiler sources,
runtime data and standard modules. `OUTPUT/bin/hs run SOURCE [args...]` uses
eager in-process execution; `build SOURCE OUTPUT` uses the native AOT compiler.
The directory can move and runs without the original checkout, Python or gcc.
This is not a static cross-platform distribution: Linux, shell utilities and
host libc/shared libraries for eager FFI remain dependencies. It adds neither
first-call compilation nor tiering. Existing output directories are refused.

### Software RGB drawing foundation
`std.gfx` is a pure-hs drawing module. A surface is `[width, height, pixels]`,
with row-major packed RGB24 Int pixels. `surface(w,h,color)` allocates at most
1,048,576 pixels; dimensions are positive and at most 4096. `pixel` clips writes
outside the surface; `sample` rejects out-of-range reads. `rect` fills a clipped
half-open rectangle `[x,x+w) x [y,y+h)`; nonpositive extents draw nothing.
`blit(dst,src,x,y)` copies an entire source with clipping and snapshots the
source when pixels alias, so overlapping self-blits are deterministic.
Coordinates/extents are bounded Ints in [-1048576,1048576], excluding Bool;
colors are Ints in [0,0xffffff]. Validation precedes mutation. Callers must not
modify the surface's dimensions or pixel-list structure. This is software
raster storage only: no hardware framebuffer, font, input or window system.

### Experimental Multiboot2 framebuffer kernel
The kernel's optional Multiboot2 header requests640x480x32. Legacy Multiboot1
boot remains unchanged. `kernel/kframebuffer.hs` discovers and validates a
direct RGB framebuffer, maps device pages supervisor-writable/cache-disabled,
and draws clipped pixels/rectangles. `std.fbinfo.decode` validates byte tags
before mapping: byte-aligned8-bit RGB channels,24/32bpp, bounded dimensions,
pitch and memory extent. The initial implementation supports physical buffers
in [1GiB,4GiB) only, to avoid silently remapping the initial RAM identity map.
Boot without a supported tag raises; it never guesses a hardware address.

GRUB video setup and an ISO are needed for this path; QEMU's direct `-kernel`
Multiboot1 route does not supply the tested graphics mode. The demo is a static
software-drawn panel, not a window manager, desktop, font renderer or hardware
GPU driver. Firmware/real-machine compatibility is unverified. Protocol layout:
https://raw.githubusercontent.com/rhboot/grub2/master/include/multiboot2.h

### Formatter control-byte preservation
Canonical formatting preserves the decoded contents of string literals.
Only the language's supported escapes (`\n`, `\t`, `\r`, `\0`, `\"`, `\\`)
are emitted. Other literal ASCII control bytes remain literal bytes inside
strings; the formatter must not invent Unicode escapes that the parser does
not decode. Unknown source escapes retain the existing literal-next-character
behavior. This adds no escape syntax or Unicode semantics.

### Tiny bitmap labels
`std.font` is an original fixed5x7 bitmap label font, not a Unicode font engine.
`glyph(character)` returns seven fresh5-bit rows (bit4 is the left pixel).
It contains A-Z, digits, spaces and the listed punctuation; ASCII lowercase
folds to uppercase. Other characters use the question-mark glyph. Exactly
one character is required. UTF-8 byte-vs-character behavior remains the
existing backend limit: portable label input is ASCII only.
`measure(text, scale)` returns `[width,height]` in6x8 cells, including trailing
cell spacing. Newline starts another row. Empty text measures `[0,0]`.
`draw(surface,x,y,text,color,scale)` uses the existing RGB surface contract,
transparent background and clipped foreground pixels. No wrapping, tab stops,
kerning or antialiasing. Scale is an integer1..16; labels are at most1024
characters. Invalid inputs fail before modifying pixels. Bounds/color checks
match `std.gfx`. Surface storage must remain unmodified by the caller.
