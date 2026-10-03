# holyshit tutorial (10 นาที)

ทุกบล็อก ```hs ในไฟล์นี้ถูกรันจริงโดย `tests/test_docs.py` —
`# =>` คือ stdout ที่ต้องตรง (รันรวมกันทั้งไฟล์ตามลำดับ)

## 1. print กับค่า

```hs
print "hello"
# => hello
print 1 + 2, 3 * 4
# => 3 12
print true, false, null
# => true false null
```

## 2. ตัวแปร ฟังก์ชัน ขอบเขต

```hs
x = 10
def add(a, b):
  return a + b
print add(x, 5)
# => 15
```

มีแค่ `def` ที่สร้าง scope ใหม่ — `if`/`while`/`for` ไม่สร้าง
(เหมือน Python). เขียน global จากในฟังก์ชันด้วย `global`:

```hs
n = 0
def bump():
  global n
  n = n + 1
  return n
print bump()
print bump()
print n
# => 1
# => 2
# => 2
```

## 3. List / Dict / Str

```hs
l = [1, "two", true]
print len(l)
# => 3
print l[0], l[-1]
# => 1 true
append(l, 4)
print l
# => [1, two, true, 4]
print l[1:3]
# => [two, true]
print "hello"[1:4]
# => ell
d = {"a": 1}
d["b"] = 2
print d["a"] + d["b"]
# => 3
```

## 4. เงื่อนไข ลูป

```hs
for i in range(3):
  print i
# => 0
# => 1
# => 2
s = 0
for x in [10, 20]:
  s = s + x
print s
# => 30
i = 0
while i < 2:
  i = i + 1
print i
# => 2
```

`and`/`or` คืน operand (ไม่ใช่ Bool): `0 or 12` ได้ `12`,
`[] and 7` ได้ `[]`:

```hs
print 0 or 12
# => 12
print 1 and 7
# => 7
print not ""
# => true
```

## 5. error กับ try

```hs
try:
  print 1 + "a"
except as e:
  print e
# => cannot add Int and Str at line 2
try:
  print "body"
finally:
  print "fin"
# => body
# => fin
```

bare `raise` นอก `try` ทำให้โปรแกรมจบด้วย error ทาง stderr
(บล็อก `hs-norun` แบบนี้ไม่ถูกรันในเทส):

```hs-norun
raise "boom"
```

## 6. module

```hs-norun
import std.str
print std.str.trim("  hi  ")
```

`import` หาไฟล์จาก: โฟลเดอร์ของโปรแกรม → `HSPATH` → cwd (คั่นด้วย `:`)
`std/` อยู่ในโฟลเดอร์ repo จึงต้องชี้ `HSPATH` ที่ตัว repo:

```sh
HSPATH=/path/to/holyshit python3 interp.py prog.hs
```

โค้ดบล็อกนี้ถูกรันจริงในเทส (`HSPATH` ชี้ที่ repo)

## 7. ต่อไป

- อยากเรียก C: อ่าน `../AGENTS.md` หัวข้อ `extern`
- อยากแตะ hardware ตรง: หัวข้อ `unsafe:`
- อยากได้ binary ไม่พึ่ง gcc / บูตเครื่องจริง: `x64-subset.md`, `kernel.md`
- อยากให้ editor ช่วย: `lsp.md`
