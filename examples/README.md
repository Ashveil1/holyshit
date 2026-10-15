# tour: ตัวอย่างที่รันได้จริงทุกไฟล์

ทุกไฟล์ใน `examples/` ถูกรันจริงโดย `tests/test_examples.py` (17 เคส) —
ตัวอย่างพังแล้วเทสจะแดง ไม่ใช่เอกสารเพี้ยนเงียบ ๆ

| ไฟล์ | เรื่อง |
|---|---|
| `01_basics.holy` | ค่า ตัวแปร ฟังก์ชัน เงื่อนไข ลูป `and/or/not` |
| `02_strings.holy` | Str: `split`/`join`/`find` slicing `str()` |
| `03_collections.holy` | List + Dict (key เป็น Str) ลูปซ้อน `break/continue` |
| `04_functions.holy` | recursion, closure, ฟังก์ชันเป็นค่า, `global` |
| `05_errors.holy` | `try/except/finally/raise` รวมกรณี raise ใน handler |
| `06_modules.holy` | `import` + `std.str` / `std.list` + closure เข้า stdlib |
| `07_extern.holy` | libc, `-lm`, และไฟล์ `.c` ผ่าน C ABI |
| `08_unsafe.holy` | `I64/U64/Ptr`, struct, pointer เดิน, raw bytes |
| `hello.holy` `fib.holy` `closure.holy` `ffi.holy` | ตัวอย่างสั้นจากรุ่นแรก |

## รัน

```sh
python3 interp.py examples/01_basics.holy
python3 hs.py run examples/04_functions.holy          # ผ่าน gcc
HSPATH=$PWD python3 interp.py examples/06_modules.holy   # ต้องเห็น std/
```

## อ่านตามลำดับนี้ถ้าเพิ่งเริ่ม

1. `01_basics.holy` — ไวยากรณ์ทั้งหมดในไฟล์เดียว
2. `04_functions.holy` — จุดที่ภาษาต่างจาก C/Python (closure จำค่าตอน def)
3. `05_errors.holy` — error เป็น Str พร้อมบรรทัด จับได้
4. `07_extern.holy` — จุดที่เชื่อมกับภาษาอื่น
5. `08_unsafe.holy` — จุดที่แตะ hardware ได้
