# AGENTS.md — holyshit (hs) v0.4.0 language reference for AI coding agents

Read this file before writing or fixing `.hs` code. It is the complete
working reference. `SPEC-v1.md` has design rationale; this file has rules.

## Run

```sh
python3 interp.py prog.hs [args...]        # run now (reference behavior)
python3 hs.py check prog.hs                # syntax+scope only, no output binary
python3 hs.py build prog.hs [-o prog]      # native binary
python3 hs.py run prog.hs [args...]        # build to temp and run
python3 interp.py --json prog.hs           # errors as {"file","line","message"} on stderr
python3 hs.py --json check|build ...       # same JSON error contract
```

Both backends print byte-identical stdout. If they differ, the NATIVE side
is usually right about nothing — file a bug, don't work around it.

## Syntax (indent like Python, but NOT Python)

- Block starts after a line ending with `:` + indented body. No braces, no `;`.
- Newline ends a statement. `#` and `//` are comments to end of line.
- `print x` / `print(x)` / `print x, y` all work; space-separated + trailing newline.
  Bare `"str"` on its own line also prints. `Print` (capital P) is WRONG (legacy v0.3).
- `//` is a COMMENT, not floor division. `/` always returns Float.
- Types are dynamic; never declare them outside `unsafe:`/`extern:`.

## Values

`Int` (64-bit) `Float` `Str` (UTF-8) `Bool` (`true`/`false`) `Null` (`null`)
`List` (mixed ok) `Dict` (Str keys only) `Func` (first-class).

- `+`: numbers (Int+Float→Float), Str+Str concat, List+List concat. Else runtime error.
- `== !=` work across types (just false). `< > <= >=` need same kind (Str ok).
- Truthiness: `false null 0 "" [] {}` are false, everything else true.
- Index: `a[i]` (negative ok), `d["k"]`, slice `s[a:b]`/`s[:b]`/`s[a:]` (Str+List).
- String escapes: `\n \t \" \\`. No multiline strings.

## Functions and scope

```
def fib(n):
  if n < 2:
    return n
  return fib(n - 1) + fib(n - 2)
```

- `return` with no value → Null. `global x` to write globals (Python rules).
- Blocks do NOT make scopes; only `def` does.
- **Closures capture BY VALUE at `def`** (native). Do NOT rely on seeing later
  reassignments of the outer var. No mutual recursion between nested funcs.
- Call with wrong arity, or call a non-function → runtime error with line number.

## Control flow and errors

`if/elif/else`, `while`, `for x in LIST|range()|dict-keys`, `break`/`continue`.
`try:` / [`except:` [`as e`]] / [`finally:`] — need at least one of except/finally.
`e` is a Str `"msg at line N"`. `finally` runs on every exit (native too).
`raise "msg"` throws (Str only); bare `raise` re-throws inside `except`
(function boundaries reset it — don't rely on bare `raise` across calls).

## Modules

- `import mod`, `import pkg.mod` (dots → path). Found in program dir,
  then `HSPATH` entries (`:` separated), then cwd.
- Missing parent packages are created empty automatically.
- Attribute access any depth: `std.str.trim("  x  ")`.
- Circular imports are a RUNTIME error, not compile time.

## unsafe: (low-level, static)

```
unsafe:
  Ptr p = alloc(16)
  *p = 4660
  print *p
```

- Types ONLY `I64 U64 Ptr` + struct pointers `Name*`. Literals adapt.
  NEVER mix I64/U64 (error). Plain and struct pointers mix freely (addresses).
- `/` `%` truncate like C (unlike safe `/` which returns Float).
- `and/or/not` return I64 0/1. `p + n` moves bytes (scaled by sizeof for struct
  pointers). `as_ptr(int)` / `as_int(p)` accept struct pointers too.
- `load8/load32/store8/store32`, `alloc(n)` (zeroed, GC'd, no free).
- `struct Name:` with scalar/`Struct*`/array fields (all 8 bytes, no padding).
  `Name* p = alloc(sizeof(Name))`, `p.field`, `p.arr[i]`, `p.field = v`
  (bounds+null checked, volatile in native). `sizeof(I64)` is 8.
- `asm("...")` works in NATIVE builds only (interpreter errors clearly).
- Allowed inside: typed decls, `*p = v`, `if`/`while`, `print`, shared statements.
  NO `def`, NO `for` (use `while`), NO `try`, NO extern calls, NO strings/lists.
- Dynamic vars are readable (auto-unboxed to I64); writing out auto-boxes.

## extern: (call C / .so / any C-ABI language)

```
extern:
  I64 puts(Str s)
extern from "m":
  F64 sin(F64 x)
extern from "helper.c":
  I64 hs_add3(I64 a, I64 b, I64 c)
```

- Signature types: `U0` (void, return only) `I64 U64 F64 Str Ptr`.
- `from`: omitted = libc; bare name = `-l`; path with `/` = dlopen; `.c` = compiled+linked.
- Top level only. Safe code only (not `unsafe:`, not kernel).
- No structs, callbacks, or variadics — write a C wrapper for those.

## Builtins (both hosted backends; x64 freestanding has its own subset)

Core: `print len range str int float input open read write close`
Text/containers: `append split find join`
Files (agent kit): `read_text write_text append_text exists ls mkdir`
JSON: `json_parse json_str json_load json_save`
Process: `argv()→List` (no prog name) `env(name)→Str|Null` `system(cmd)→Int status`
Net (http only): `tcp_connect/send/recv/close tcp_listen/accept http_get(url)→body`
Kernel-surface (xkernel freestanding): `ticks readkey pmm_alloc pmm_total pmm_free` (+ unsafe alloc/load/store/as_*)

### x64 backend subset (`hs.py xbuild` / `xkernel`)

Has: Int (62-bit), Str values (literals, `+` concat, `len`, `==`, `<`), Bool, `null`,
`not/and/or`, `if/elif/else`, `while`, `for` (`for i in range([a,] b)` lowers to a
counter loop — no List allocated; `for c in <str>` yields 1-char Str),
`break`/`continue`, `def` (recursion + closures), `str()`, `int()`, `len()`,
`print`, `unsafe:` I64/U64/Ptr + structs, kernel builtins above.

Missing (compile error, on purpose): Float, List, Dict, `try`, `import`,
slicing, attribute access, `extern`. Standalone `range()` outside `for` is also
an error (it never materializes a list). `/` truncates like C here, not hs.

Value representation: low 2 bits are the tag — `01` Int (`v<<2|1`),
`10` Bool (0x02/0x0A), `11` Null (0x03)/Unbound (0x0B), `00` heap object
(`[kind][len][bytes]` for Str, `[kind][code][caps]` for Func). Heap = bump
allocator, never frees. Type errors print `type error` and exit(1)/halt.

Inside `unsafe:` values stay raw machine words (literals untagged);
use `as_ptr(x)` / `as_int(x)` to cross from tagged dynamic values.

## Gotchas (read twice)

1. `//` starts a comment. Always.
2. `;` `{` `}` do not exist. `Print` capital is legacy and fails.
3. `for i in 0..5` does not exist — use `range(5)`.
4. `x = 010` is decimal 10, not octal. `0xFF` hex works.
5. Dict keys must be Str. `d[k] = v` creates keys; missing read is an error.
6. `print` of a Float prints shortest form (`3.5`, `0.0` with `.0` kept).
7. Errors always look like `error: <msg> at line N` (stderr, exit 1).
8. `import` runs the module body once; module state is shared.
9. Integer division does not exist — `7 / 2` is `3.5`.
10. `str + int` is an error, never implicit. Convert explicitly.
11. `print (expr) trailing` breaks: `print (1+2)*3` parses `(1+2)` as the
    print-argument and chokes on `*3`. Write `print 1 + 2` or `print ((1+2)*3)`.
    (`hs fmt` rewrites this correctly automatically.)

## Fix loop for agents

1. `hs.py check` (fast) → `interp.py` (behavior) → `hs.py build` (native parity).
2. With `--json`, parse stderr: fix `line`, re-run. Line numbers track the `.hs` source.
3. Run `hs fmt` before editing foreign code; keep diffs canonical.
4. New failing case? Add `tests/<name>.hs` + `.expected`/`.fail` (+`.args`/`.stdin`/`.env`
   as needed) and run `tests/test.py` + `tests/test_native.py` (+`test_fmt.py`).
