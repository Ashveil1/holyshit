# stdlib — `std/` (เขียนด้วย hs ล้วน)

ใช้ด้วย `HSPATH=std` (หรือวางไฟล์ข้างโปรแกรม):

```sh
HSPATH=std python3 interp.py prog.hs
```

```hs-norun
import std.str
import std.list
print std.str.trim("  hi  ")
```

## std.str — ข้อความ

| ฟังก์ชัน | ทำอะไร |
|---|---|
| `trim(s)` | ตัด space หัวท้าย (`" \t\n\r`) |
| `pad_left(s, w)` / `pad_right(s, w)` | เติม space ให้ยาว `w` |
| `starts_with(s, pre)` / `ends_with(s, suf)` | ตรวจ prefix/suffix |
| `lines(s)` | แยกบรรทัดเป็น List (`split(s, "\n")`) |

รันบน x64 ได้ (xbuild/xkernel) — ใช้แค่ slice/index/while/len.

## std.list — ลิสต์เชิงฟังก์ชัน

| ฟังก์ชัน | ทำอะไร |
|---|---|
| `map(f, xs)` | List ใหม่จาก `f(x)` ทุกตัว |
| `filter(f, xs)` | เฉพาะตัวที่ `f(x)` เป็นจริง |
| `fold(f, acc, xs)` | สะสม `acc = f(acc, x)` |
| `any(f, xs)` / `all(f, xs)` | มี/ทุกตัวเป็นจริงไหม |

รันบน x64 ได้ (โชว์ closure ด้วย)

## std.heap — malloc/free บน unsafe (สไตล์ K&R)

| ฟังก์ชัน | ทำอะไร |
|---|---|
| `heap_init(nbytes)` | เตรียม region (เรียกครั้งเดียว) |
| `malloc(nbytes)` | จอง → address (Int), `0` ถ้าเต็ม |
| `free(p)` | คืน (รวมบล็อกข้างเคียง) |
| `heap_free()` / `heap_nblocks()` | ที่ว่าง / จำนวนบล็อก |

ที่อยู่เป็น Int ธรรมดา (`as_int`/`as_ptr` ข้ามฝั่ง), single-thread.
ใช้บน x64 ได้ถ้าโปรแกรมอยู่ใน subset ของ `unsafe:` ทั้งหมด
