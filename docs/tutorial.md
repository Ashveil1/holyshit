# holyshit tutorial (10 minutes)

Every ```hs block in this file is actually run by `tests/test_docs.py` -
`# =>` is the stdout that must match (all blocks run together in order)

## 1. print and values

```hs
print "hello"
# => hello
print 1 + 2, 3 * 4
# => 3 12
print true, false, null
# => true false null
```

## 2. Variables, functions, scope

```hs
x = 10
def add(a, b):
  return a + b
print add(x, 5)
# => 15
```

Only `def` creates a new scope - `if`/`while`/`for` do not
(like Python). Write a global from inside a function with `global`:

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

## 4. Conditions and loops

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

`and`/`or` return an operand (not a Bool): `0 or 12` gives `12`,
`[] and 7` gives `[]`:

```hs
print 0 or 12
# => 12
print 1 and 7
# => 7
print not ""
# => true
```

bitwise works on Int only (Bool does not count):

```hs
mask = 0xFF
v = 0x1234
print v & mask
print v | 0xF0
print v ^ 0xFFFF
print ~v
print 1 << 10
print 1024 >> 3
```

## 5. Errors and try

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

A bare `raise` outside `try` ends the program with an error on stderr
(an `hs-norun` block like this is not run in the test):

```hs-norun
raise "boom"
```

## 6. Modules

```hs-norun
import std.str
print std.str.trim("  hi  ")
```

`import` searches: the program's directory -> `HSPATH` -> cwd (colon-separated).
`std/` lives in the repo directory, so point `HSPATH` at the repo:

```sh
HSPATH=/path/to/holyshit python3 interp.py prog.holy
```

(This code block really runs in the test with `HSPATH` pointing at the repo.)

## 7. Next steps

- Want to call C: read `../AGENTS.md` under `extern`
- Want to touch hardware directly: the `unsafe:` section
- Want a gcc-free binary / boot real hardware: `x64-subset.md`, `kernel.md`
- Want editor help: `lsp.md`
