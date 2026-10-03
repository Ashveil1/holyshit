# tour: ตัวอย่างที่รันได้จริงทุกไฟล์

ทุกไฟล์ใน `examples/` ถูกรันจริงโดย `tests/test_examples.py` (17 เคส) —
ตัวอย่างพังแล้วเทสจะแดง ไม่ใช่เอกสารเพี้ยนเงียบ ๆ

| ไฟล์ | เรื่อง |
|---|---|
| `01_basics.hs` | ค่า ตัวแปร ฟังก์ชัน เงื่อนไข ลูป `and/or/not` |
| `02_strings.hs` | Str: `split`/`join`/`find` slicing `str()` |
| `03_collections.hs` | List + Dict (key เป็น Str) ลูปซ้อน `break/continue` |
| `04_functions.hs` | recursion, closure, ฟังก์ชันเป็นค่า, `global` |
| `05_errors.hs` | `try/except/finally/raise` รวมกรณี raise ใน handler |
| `06_modules.hs` | `import` + `std.str` / `std.list` + closure เข้า stdlib |
| `07_extern.hs` | libc, `-lm`, และไฟล์ `.c` ผ่าน C ABI |
| `08_unsafe.hs` | `I64/U64/Ptr`, struct, pointer เดิน, raw bytes |
| `hello.hs` `fib.hs` `closure.hs` `ffi.hs` | ตัวอย่างสั้นจากรุ่นแรก |

## รัน

```sh
python3 interp.py examples/01_basics.hs
python3 hs.py run examples/04_functions.hs          # ผ่าน gcc
HSPATH=$PWD python3 interp.py examples/06_modules.hs   # ต้องเห็น std/
```

## อ่านตามลำดับนี้ถ้าเพิ่งเริ่ม

1. `01_basics.hs` — ไวยากรณ์ทั้งหมดในไฟล์เดียว
2. `04_functions.hs` — จุดที่ภาษาต่างจาก C/Python (closure จำค่าตอน def)
3. `05_errors.hs` — error เป็น Str พร้อมบรรทัด จับได้
4. `07_extern.hs` — จุดที่เชื่อมกับภาษาอื่น
5. `08_unsafe.hs` — จุดที่แตะ hardware ได้
