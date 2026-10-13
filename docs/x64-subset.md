# x64 backend subset (`hs.py xbuild`, `hs.py xkernel`)

machine code ตรง ไม่ใช้ gcc/as/ld/libc. ตาราง `builtins.md` คอลัมน์
xbuild/xkernel บอกว่า builtin ไหนใช้ได้. กฎสั้น ๆ ของ subset:

มี: Int (62-bit), Float (f64 เต็ม: คำนวณ `- * / %`, เทียบ, `print`/`float()`
แบบ shortest round-trip ตรงกับ Python), Str/List/Dict/Bool/null เต็มรูปแบบ, `not/and/or`,
`if/elif/else`, `while`, `for`, `break`/`continue`, `def` (+closure),
`try`/`except`/`finally`/`raise`, `import` (+attr โมดูล), `global`,
`str()`/`int()`/`float()`/`len()`/`print`, `json_parse`/`json_str`,
`read_mem(p, n)`,
`unsafe:` (I64/U64/Ptr + struct)

- `def` ของผู้ใช้ shadow builtin ชื่อเดียวกันได้ (เหมือน interp/native)
  แต่ชื่อที่อยู่ในรายการ builtin ของ subset นี้คงเป็น builtin เสมอ

`extern` (libc/.so) รองรับแล้ว: ELF แบบ dynamic ให้ ld.so ผูกสัญลักษณ์ ไม่ต้องมี gcc; ชนิด I64/U64/F64/Ptr/Str ≤6 อาร์กิวเมนต์

ไม่มี (compile error ตั้งใจ): `extern` จาก `.c`,
`open/read/write/close` บน kernel, `json_load`/`json_save` บน kernel, `tcp_*`,
`http_get`,
ส่งโมดูลเข้าคำนวณ/call/index, `print`/`str` ของ
Func ที่ประกาศเอง (builtin ใช้เป็นค่าได้ เห็น `<builtin str>`)

`m = mod` / `m = pkg.sub` เป็น alias ได้ (ไม่เสียค่าใช้จ่ายตอนรัน,
`m.attr` เหมือนเดิมทุกอย่างรวมถึง `print m`) — แต่ห้ามส่งโมดูลเข้า
function/operator/index (ชื่อที่ assign ค่าทับ alias กลายเป็นค่าปกติ)

hosted (`xbuild`) มีเพิ่ม: `argv()` (List ของ argv[1:]), `input()`
(หนึ่งบรรทัด, EOF เปล่าๆ = error), `env(name)` (ขาด = null),
`open(path, "r"/"w")` → File (แสดง `<file PATH>`), `read(f)` ทั้งไฟล์,
`write(f, s)` (คืน byte count), `close(f)` (ปิดซ้ำ = no-op) —
error เป็น `errno N` (interp โชว์ strerror),
`json_load`/`json_save` (อ่าน/เขียนไฟล์ผ่าน File runtime),
`scall(nr, a1..a6)` — `syscall` ดิบ (ใช้เขียน
user program ที่คุยกับ kernel ของเรา เช่น `kernel/uush.hs`) แต่
`xkernel` ไม่มี เพราะ ring 0 เรียก `syscall` แล้ว `sysret` จะตกไป
ring 3 ผิดทาง

## กับดักที่ต้องจำ

- `/` ตัดทศนิยมแบบ C (hosted ได้ Float)
- Str index/slice/split นับเป็น **byte** (non-ASCII ต่างจาก interp)
- `split` sep ว่าง raise (interp/native crash แทน)
- หารด้วยศูนย์บน kernel เป็น HW `#DE` (halt) ไม่ใช่ error จับได้
- อ่านตัวแปรที่ยังไม่เคย assign = error `unknown variable` (ไม่ใช่ขยะ)
- `and`/`or` **ไม่ short-circuit** — ทั้งสองข้างรันเสมอ ต้องเขียน bound check
  เป็นเรียกแยก (`js_at(s, i, n)` ใน `runtime/json.hs`) ไม่งั้น `s[i]`
  นอกช่วงจะ raise
- `json_*` ถูกคอมไพล์มาจาก `runtime/json.hs` (โมดูลส่วนตัว `<json>` ที่
  x64gen ใส่เข้า image เมื่อโปรแกรมเรียกมัน) — ไม่ใช่ API: `import`
  เอาไปเองได้ถ้า repo อยู่บน HSPATH แต่ตัวที่ต้องใช้ `type_name` (hook
  ส่วนตัว) จะคอมไพล์ไม่ผ่าน

## ตัวอย่างผ่าน / ไม่ผ่าน

```hs
for i in range(3):
  print i
# => 0
# => 1
# => 2
print "ab"[1:]
# => b
print [3][0:]
# => [3]
```

```hs-norun
print 1.5 + 2.5  # Float: 4.0
import os        # ไม่มีโมดูลนี้: cannot find module
print argv()     # argv: not in x64 subset
```

## Recursion ไม่จบ (runaway recursion)

ทุก backend รายงาน `error: stack overflow (recursion too deep)` (exit 1):
interp ผ่าน recursion limit, native ผ่าน SIGSEGV handler, x64 ผ่าน guard ที่ทางเข้า
ฟังก์ชัน (เทียบ rsp กับ stack ที่ใช้ไป 7MB; ถ้า `ulimit -s` เล็กกว่านั้นยัง segfault)
