# cheatsheet — ทั้งภาษาในหน้าเดียว

กระชับที่สุดสำหรับคน/AI ที่รู้ Python อยู่แล้ว กฎฉบับเต็มอยู่ที่
[`../AGENTS.md`](../AGENTS.md)

## รัน

```sh
python3 interp.py prog.hs        # ตีความ (อ้างอิงความจริง)
python3 hs.py check prog.hs      # syntax + scope
python3 hs.py run prog.hs        # native ผ่าน gcc
python3 hs.py fmt prog.hs -w     # จัดรูป canonical
```

## ไวยากรณ์

```hs
x = 1                       # กำหนดค่า (ไม่มี : และไม่มี type)
print x, x + 1              # เว้นวรรค + newline ท้าย
print "str"                 # Str ต่อกันได้
"bare string"               # บรรทัดเดียวที่เป็น string ก็ print

def f(a, b = 0):            # default arg: ไม่มี
  return a + b              # return ไม่มีค่า -> null

if c:
  x = 1
elif d:
  x = 2
else:
  x = 3

while c:
  break                    # continue ก็มี

for x in xs:                # xs = List | Str | range() | dict keys
  print x

try:
  risky()
except as e:               # e เป็น Str "msg at line N"
  print e
finally:
  cleanup()                 # ต้องมี except หรือ finally อย่างน้อยตัวหนึ่ง
                            # finally รันแม้ handler จะ raise ต่อ

raise "msg"                 # Str เท่านั้น; ใน except ใช้ raise ซ้ำได้
assert x > 0, "msg"        # ไม่จริง = raise "msg" (ไม่ใส่ msg = "assertion failed")
print [x * 2 for x in xs if x > 0]   # list comprehension (1 for + optional if)
import mod.sub              # หาใน: โฟลเดอร์โปรแกรม -> HSPATH -> cwd
global x                    # เขียนชื่อระดับ module จากใน def
```

คอมเมนต์ `#` หรือ `//` (ท้ายบรรทัด) ไม่มี `;` `{` `}` `++`
ไม่มี `//` หาร (ใช้ `/` ซึ่งได้ Float) ไม่มี `0..5` (ใช้ `range(5)`)

## ค่า

| ชนิด | เขียน | หมายเหตุ |
|---|---|---|
| Int | `42`, `0xFF`, `-7` | 64-bit (x64 subset: 62-bit) |
| Float | `3.5` | hosted เท่านั้น |
| Str | `"a\nb"` | escape: `\n \t \" \\` |
| Bool | `true`, `false` | falsy: `false null 0 "" [] {}` |
| Null | `null` | |
| List | `[1, "a"]` | ผสมชนิดได้ `append` ต่อท้าย |
| Dict | `{"k": 1}` | key ต้องเป็น Str; อ่าน key ที่ไม่มี = error |
| Func | `def`, lambda ไม่มี | first-class เก็บในตัวแปร/ส่งเป็น argument ได้ |

## ตัวดำเนินการ

`+ - * / %` (`/` ได้ Float เสมอ), `== != < > <= >=`,
`and or not` (คืน operand ไม่ใช่ Bool), `a[i]`, `a[i] = v`,
`s[a:b]` (ค่าติดลบได้), `len(x)`

ternary: `a if cond else b` (ประเมินเฉพาะฝั่งที่เลือก, ซ้อนได้ ขวาไปซ้าย)

bitwise (Int เท่านั้น — Bool ไม่ใช่ Int):

```hs
print 6 & 3, 6 | 3, 6 ^ 3
print ~0
print 1 << 10
print 1024 >> 3
print 0x83 & ~0x10
```

ผลคือ `2 7 5` / `-1` / `1024` / `128` / `131`
bitwise ผูกแน่นกว่า `+ -` แต่หลวมกว่า `* / %`; shift count ต้อง 0..63

- `+` ได้กับ Int+Float, Str+Str, List+List — ผสมชนิด = error
- `< >` ต้องเป็นชนิดเดียวกัน (Str เทียบกันได้)
- `str + int` ผิดเสมอ ต้อง `str(x) + str(y)` (ไม่มี implicit)

## builtin ที่ใช้บ่อย

```hs
print(x, y)   len(x)   range(n) | range(a, b)   str(x)   int(x)
append(xs, v)        split(s) | split(s, sep)    find(s, sub)
# เขียนเป็น method ก็ได้: xs.append(v)  s.split(",")  s.find(sub)  ",".join(xs)
join(sep, xs)        input()   open/read/write/close (hosted)
argv()  env(k)  system(cmd)          json_*  read_text/write_text (hosted)
read_mem(p, n)  # n ไบต์ดิบที่ address p เป็น Str (ทุก backend)
```

`alloc/load8/load32/store8/store32/as_ptr/as_int` ใช้ใน `unsafe:` เท่านั้น

prelude (เขียนด้วย hs เอง ใส่ให้เฉพาะเมื่อโปรแกรมเรียกใช้ และไม่ได้ `def`/ตั้งชื่อเดียวกันเอง):
`abs(x)  min(xs) | min(a, b)  max(xs) | max(a, b)  sum(xs)  sorted(xs)  reversed(xs)  upper(s)  lower(s)`
(`sorted` เป็น merge sort คืน list ใหม่; ไม่มีตัวหาร int — ใช้ `int(a / b)`)
ดูตารางครบทุกตัว + backend ที่รองรับที่ [`builtins.md`](builtins.md)

## `unsafe:` — ชนิดคงที่ (ไม่มี dynamic)

```hs
unsafe:
  struct Point:
    I64 x
    I64 y

  Point* p = alloc(sizeof(Point))
  p.x = 3
  p.y = 4
  print p.x + p.y
  Point* q = p + 1           # เดินทีละ sizeof
  print q - p
  print 7 / 2                # 3 (ตัดทศนิยมแบบ C)
  print 1 and 2             # 2 -> I64
  asm("nop")                 # native build เท่านั้น
```

- ใช้ได้: typed decl (`I64 U64 Ptr Name*`), `*p = v`, struct, `p.f`, `p.arr[i]`,
  `sizeof(T)` (ทุกช่อง 8 bytes ไม่มี padding), `if/while`, `print`
- raw 64-bit: `load64(p)` / `store64(p, v)` (ไม่ tag — ใช้กับ page table entry)
- ใช้ไม่ได้: `def`, `for`, `try`, `Str/List/Float`, extern, string
- ค่าใน `unsafe:` เป็น machine word ดิบ — ข้ามฝั่งด้วย `as_ptr`/`as_int`

## `extern:` — เรียก C / ภาษาอื่น

```hs
extern:                     # libc
  U64 strlen(Str s)
  I64 abs(I64 x)

extern from "m":             # -lm
  F64 sin(F64 x)

extern from "helper.c":      # คอมไพล์+ลิงก์ให้
  I64 triple(I64 x)
```

ชนิดใน signature: `U0 I64 U64 F64 Str Ptr` — ไม่มี struct/callback/variadic
และไม่มี implicit conversion (ต้องแปลงเองทุกครั้ง) — hosted เท่านั้น

## error

ข้อความ error ทั้งหมดของภาษาอยู่ที่ [`errors.md`](errors.md) (ดึงจาก source อัตโนมัติ)

ทุก error เป็น Str `"message at line N"` ไม่มี exception object
ไม่จับ = พิมพ์ `error: <msg> at line N` ที่ stderr แล้ว exit 1
`hs.py --json check/build` และ `interp.py --json` ให้ผลเป็น JSON

## gotchas ที่ทำให้พังบ่อย

1. `//` คือคอมเมนต์ — `/` คือหาร
2. `print (1+2)*3` พัง → `print ((1+2)*3)`
3. `for i in 0..5` ไม่มี → `range(5)`
4. block indent ต้องสม่ำเสมอ และ `def` เท่านั้นที่สร้าง scope
5. closure จำค่า **ตอน `def`** (ไม่ใช่ตอนเรียก)
6. `print` เว้นวรรค ไม่ใช่ comma แบบ Python
7. x64/kernel subset ไม่มี Float/Dict/extern/argv — ดู `x64-subset.md`
