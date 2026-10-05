# x64 backend subset (`hs.py xbuild`, `hs.py xkernel`)

machine code ตรง ไม่ใช้ gcc/as/ld/libc. ตาราง `builtins.md` คอลัมน์
xbuild/xkernel บอกว่า builtin ไหนใช้ได้. กฎสั้น ๆ ของ subset:

มี: Int (62-bit), Str/List/Bool/null เต็มรูปแบบ, `not/and/or`,
`if/elif/else`, `while`, `for`, `break`/`continue`, `def` (+closure),
`try`/`except`/`finally`/`raise`, `import` (+attr โมดูล), `global`,
`str()`/`int()`/`len()`/`print`, `read_mem(p, n)`,
`unsafe:` (I64/U64/Ptr + struct)

- `def` ของผู้ใช้ shadow builtin ชื่อเดียวกันได้ (เหมือน interp/native)
  แต่ชื่อที่อยู่ในรายการ builtin ของ subset นี้คงเป็น builtin เสมอ

ไม่มี (compile error ตั้งใจ): Float, `extern`,
`open/read/write/close` บน kernel, `tcp_*`, `http_get`, `json_*`,
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
print 1.5        # Float: not in x64 subset
import os        # ไม่มีโมดูลนี้: cannot find module
print argv()     # argv: not in x64 subset
```
