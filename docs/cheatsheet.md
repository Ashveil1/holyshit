# cheatsheet - the whole language on one page

The most compact reference for people/AI who already know Python. The full
rules live in [`../AGENTS.md`](../AGENTS.md)

## Native install/run/build (Linux x86-64)

```sh
sh scripts/install-native.sh "$HOME/holyshit-native"
"$HOME/holyshit-native/bin/hs" run prog.holy
"$HOME/holyshit-native/bin/hs" build prog.holy /tmp/prog-hs
```

New destination, existing parent; no Python/gcc needed. Hosted subset,
run/build only, no interpreter fallback. See [native-install.md](native-install.md).

## Development/reference tools (Python)

```sh
python3 interp.py prog.holy        # interpret (reference of truth)
python3 hs.py check prog.holy      # syntax + scope
python3 hs.py run prog.holy        # development CLI, backend selection/fallback
python3 hs.py fmt prog.holy -w     # canonical formatting
```

## Syntax

```hs
x = 1                       # assignment (no : and no type)
print x, x + 1              # space-separated + trailing newline
print "str"                 # Str can be concatenated
"bare string"               # a lone string line also prints

def f(a, b = 0):            # default arg: none
  return a + b              # return with no value -> null

if c:
  x = 1
elif d:
  x = 2
else:
  x = 3

while c:
  break                    # continue exists too

for x in xs:                # xs = List | Str | range() | dict keys
  print x

try:
  risky()
except as e:               # e is a Str "msg at line N"
  print e
finally:
  cleanup()                 # at least one of except/finally is required
                            # finally runs even if the handler raises on

raise "msg"                 # Str only; bare raise re-raises inside except
assert x > 0, "msg"        # false = raise "msg" (no msg = "assertion failed")
print [x * 2 for x in xs if x > 0]   # list comprehension (1 for + optional if)
for i, x in enumerate(xs):          # tuple loop vars + enumerate (prelude)
def greet(name, hi="hello"):        # default args: a call f("a") gets the default
  return hi + ", " + name           # appended at parse time (evaluated per call; not on methods)
import mod.sub              # searched in: program dir -> HSPATH -> cwd
global x                    # write a module-level name from inside def
```

Comments are `#` or `//` (end of line). No `;` `{` `}` `++`.
No `//` division (use `/`, which yields Float). No `0..5` (use `range(5)`).

## Values

| Type | Written | Notes |
|---|---|---|
| Int | `42`, `0xFF`, `-7` | 64-bit (x64 subset: 62-bit) |
| Float | `3.5` | hosted only |
| Str | `"a\nb"` | escapes: `\n \t \" \\` |
| Bool | `true`, `false` | falsy: `false null 0 "" [] {}` |
| Null | `null` | |
| List | `[1, "a"]` | mixed types ok; `append` adds at end |
| Dict | `{"k": 1}` | keys must be Str; reading a missing key = error |
| Func | `def`, no lambda | first-class: store in vars / pass as arguments |

## Operators

`+ - * / %` (`/` always yields Float), `== != < > <= >=`,
`and or not` (returns an operand, not a Bool), `a[i]`, `a[i] = v`,
`s[a:b]` (negatives ok), `len(x)`

ternary: `a if cond else b` (evaluates only the chosen side, nests right-to-left)

bitwise (Int only - Bool is not an Int):

```hs
print 6 & 3, 6 | 3, 6 ^ 3
print ~0
print 1 << 10
print 1024 >> 3
print 0x83 & ~0x10
```

Result: `2 7 5` / `-1` / `1024` / `128` / `131`
bitwise binds tighter than `+ -` but looser than `* / %`; shift count must be 0..63

- `+` works on Int+Float, Str+Str, List+List - mixing types = error
- `< >` requires same types (Str compares with Str)
- `str + int` is always wrong; use `str(x) + str(y)` (no implicit conversion)

## Common builtins

```hs
print(x, y)   len(x)   range(n) | range(a, b)   str(x)   int(x)
append(xs, v)        split(s) | split(s, sep)    find(s, sub)
# method form works too: xs.append(v)  s.split(",")  s.find(sub)  ",".join(xs)
join(sep, xs)        input()   open/read/write/close (hosted)
argv()  env(k)  system(cmd)          json_*  read_text/write_text (hosted)
read_mem(p, n)  # n raw bytes at address p as a Str (every backend)
```

`alloc/load8/load32/store8/store32/as_ptr/as_int` are only allowed inside `unsafe:`

prelude (written in hs itself, included only when the program calls it and
does not `def`/reuse the same name):
`abs(x)  min(xs) | min(a, b)  max(xs) | max(a, b)  sum(xs)  sorted(xs)  reversed(xs)  upper(s)  lower(s)`
(`sorted` is a merge sort returning a new list; there is no int division -
use `int(a / b)`)
See the full table with per-backend support in [`builtins.md`](builtins.md)

## `unsafe:` - static types (no dynamic)

```hs
unsafe:
  struct Point:
    I64 x
    I64 y

  Point* p = alloc(sizeof(Point))
  p.x = 3
  p.y = 4
  print p.x + p.y
  Point* q = p + 1           # steps by sizeof
  print q - p
  print 7 / 2                # 3 (C-style truncation)
  print 1 and 2             # 2 -> I64
  asm("nop")                 # native build only
```

- Allowed: typed decl (`I64 U64 Ptr Name*`), `*p = v`, struct, `p.f`, `p.arr[i]`,
  `sizeof(T)` (every field is 8 bytes, no padding), `if/while`, `print`
- raw 64-bit: `load64(p)` / `store64(p, v)` (no tag - for page table entries)
- Not allowed: `def`, `for`, `try`, `Str/List/Float`, extern, string
- Values inside `unsafe:` are raw machine words - cross the boundary with `as_ptr`/`as_int`

## `extern:` - call C / other languages

```hs
extern:                     # libc
  U64 strlen(Str s)
  I64 abs(I64 x)

extern from "m":             # -lm
  F64 sin(F64 x)

extern from "helper.c":      # compiled + linked for you
  I64 triple(I64 x)
```

Signature types: `U0 I64 U64 F64 Str Ptr` - no struct/callback/variadic
and no implicit conversion (convert explicitly every time) - hosted only

## Errors

Every error message in the language lives in [`errors.md`](errors.md)
(extracted from source automatically)

All errors are Str `"message at line N"`; there is no exception object.
Uncaught = prints `error: <msg> at line N` to stderr and exits 1.
`hs.py --json check/build` and `interp.py --json` produce JSON output.

## Gotchas that break things most often

1. `//` is a comment - `/` is division
2. `print (1+2)*3` breaks -> `print ((1+2)*3)`
3. `for i in 0..5` does not exist -> `range(5)`
4. Block indent must be consistent, and only `def` creates a scope
5. A closure captures values **at `def` time** (not at call time)
6. `print` uses spaces, not Python-style commas
7. The x64/kernel subset has no Float/Dict/extern/argv - see `x64-subset.md`
