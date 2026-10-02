# holyshit — SPEC v0.3 (ง่ายกว่า Python สำหรับสคริปต์เล็ก)

## เขียนแบบ Python ได้
- ไม่ต้องประกาศ type: `x = 5` (I64 อัตโนมัติ) ของเดิม `I64 x = 5;` ยังใช้ได้
- ไม่ต้อง `;`: ขึ้นบรรทัดใหม่จบ statement `;` ยังใช้ได้ปนกัน
- `Print x` / `Print(x)` / `Print x, y` ได้หมด
- `"hello"` บรรทัดเดียว = พิมพ์เลย (แบบ HolyC)
- `#` คอมเมนต์ได้เหมือน `//`
- `for i in 0..5 { }` (ไม่รวม 5, แบบ range) แทน while
- top-level รันเลย ไม่ต้องมี main

## รัน
- JIT (แนะนำ): `node jit.js prog.HC` — compile ลง memory แล้วรันทันที ไม่เขียนไฟล์ `.wasm`
- AOT (ดูไส้ใน): `python3 compiler.py prog.HC out.wasm && node run.js out.wasm`

## Print v0.3 (แบบ Python)
`Print` คั่น args ด้วยช่องว่าง + ขึ้นบรรทัดใหม่ท้ายเสมอ ไม่มี format string แบบ printf
- `Print 42` → `42`
- `Print "hi"` → `hi`
- `Print "fib:", fib(10)` → `fib: 55`
- `Print 1, 2, 3` → `1 2 3`
- `Print` อย่างเดียว → บรรทัดว่าง
- ของเก่า `Print("%d", x)` จะพิมพ์ `%d` ออกมาด้วย ให้แก้เป็น `Print x`

## ที่มี
I64/U0/U64, ฟังก์ชัน, if/else, while, for..in, return, + - * / %, == != < > <= >=, string พิมพ์ได้อย่างเดียว (ยังเก็บลง var ไม่ได้), F64/struct/pointer/array ยังไม่มี

## ตัวอย่าง
```
# no types, no semicolons
x = 2 + 3 * 4
Print x
Print "hello"

for i in 0..5 {
  Print i
}

I64 fib(I64 n) {
  if (n < 2) {
    return n
  }
  return fib(n-1) + fib(n-2)
}
Print "fib:", fib(10)
```
