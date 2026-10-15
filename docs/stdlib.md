# stdlib — `std/` (เขียนด้วย hs ล้วน)

`import std.str` ต้องการ `std/` ให้มองเห็นเป็นโฟลเดอร์ ของ `HSPATH`
(โฟลเดอร์โปรแกรมก่อนเสมอ แล้วค่อย `HSPATH` ต่อด้วย `:`):

```sh
# จากโฟลเดอร์ repo: ชี้ HSPATH ที่ตัว repo (มี std/ อยู่ข้างใน)
HSPATH=/path/to/holyshit python3 interp.py prog.hs
# หรือก๊อป std/ ไปไว้ข้างโปรแกรมแล้ว import ตรง ๆ ไม่ต้องตั้งอะไร
```

ตัวอย่างที่รันจริงในเทส:

```hs
import std.str
import std.list

def add(a, b):
  return a + b

print std.str.trim("  hi  ")
print std.list.fold(add, 0, [1, 2, 3])
print std.str.starts_with("holyshit", "holy")
# => hi
# => 6
# => true
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

## std.bitmap — bit set บน byte (สำหรับ frame allocator, GDT/IDT slot)

bit `i` อยู่ที่ byte `i / 8` mask `1 << (i % 8)` — ทุกฟังก์ชันรับ base เป็น
Int address (จาก `alloc()`) และใช้แค่ `load8/store8` จึงรันได้ทุก backend

| ฟังก์ชัน | ทำอะไร |
|---|---|
| `bit_get/set/clear/toggle(base, i)` | อ่าน/เขียน/สลับบิตเดียว |
| `bit_reserve(base, start, count)` / `bit_release(...)` | ทำเครื่องหมายช่วงบิต |
| `bit_count_used(base, nbits)` | นับบิตที่ใช้ |
| `bit_find(base, nbits)` / `bit_find_from(..., start)` | บิตว่างแรก, `-1` ถ้าเต็ม |
| `bit_run_free(base, start, want)` | จำนวนบิตว่างติดกันจาก `start` |
| `bit_alloc_run(base, nbits, want, start)` | หาช่วงว่าง `want` ติดกัน, `-1` ถ้าไม่พอ |
| `bit_take(base, nbits, start, want)` | `alloc_run` + ทำเครื่องหมายทันที |
| `bitmap_bytes(nbits)` | จำนวน byte ที่ต้องใช้ |

> หมายเหตุ x64: ชื่อระดับโมดูลถูก resolve แบบ static — **ต้องนิยามฟังก์ชันที่ถูกเรียก
> ก่อนตัวที่เรียกมัน** (เรียงลำดับในไฟล์ให้ถูก)

## std.heap — malloc/free บน unsafe (สไตล์ K&R)

| ฟังก์ชัน | ทำอะไร |
|---|---|
| `heap_init(nbytes)` | เตรียม region (เรียกครั้งเดียว) |
| `malloc(nbytes)` | จอง → address (Int), `0` ถ้าเต็ม |
| `free(p)` | คืน (รวมบล็อกข้างเคียง) |
| `heap_free()` / `heap_nblocks()` | ที่ว่าง / จำนวนบล็อก |

ที่อยู่เป็น Int ธรรมดา (`as_int`/`as_ptr` ข้ามฝั่ง), single-thread.
ใช้บน x64 ได้ถ้าโปรแกรมอยู่ใน subset ของ `unsafe:` ทั้งหมด

## Software graphics: std.gfx

A hardware-independent RGB24 drawing foundation. Import `std.gfx`, allocate
`s = std.gfx.surface(width, height, color)`, then use `pixel(s,x,y,color)`,
`rect(s,x,y,width,height,color)`, `blit(dst,src,x,y)` and `sample(s,x,y)` through
the module. Colors are packed `0xRRGGBB`; rectangles are half-open and clipped.
Writes outside the surface are ignored; reads outside it raise. Self-blits
snapshot their source. Dimensions/pixel-list storage must remain intact.

Surface storage is `[width,height,pixels]`, limited to1,048,576 pixels and
4096 per dimension. Coordinates/extents are Ints within ±1,048,576. This module
has no framebuffer mapping, fonts, input events or windows. The software
preview in `examples/gfx_surface.hs` prints dimensions and a deterministic pixel checksum; it is not a
running desktop. Kernel execution is checked with serial output in full CI.
