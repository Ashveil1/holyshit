# x64 backend subset (`hs.py xbuild`, `hs.py xkernel`)

Direct machine code without gcc/as/ld/libc. The xbuild/xkernel columns of the
`builtins.md` table say which builtin works where. Short rules of the subset:

Includes: Int (62-bit), Float (full f64: `- * / %` arithmetic, comparisons,
`print`/`float()` with shortest round-trip matching Python), full
Str/List/Dict/Bool/null, `not/and/or`,
`if/elif/else`, `while`, `for`, `break`/`continue`, `def` (+closure),
`try`/`except`/`finally`/`raise`, `import` (+module attrs), `global`,
`str()`/`int()`/`float()`/`len()`/`print`, `json_parse`/`json_str`,
`read_mem(p, n)`,
`unsafe:` (I64/U64/Ptr + struct)

- A user `def` may shadow a same-named builtin (like interp/native),
  but names on this subset's builtin list always stay builtins

`extern` (libc/.so) is supported: dynamic ELF with ld.so binding symbols, no
gcc needed; types I64/U64/F64/Ptr/Str, up to 6 arguments

Intentionally absent (compile errors): `extern` from `.c`,
`open/read/write/close` on kernel, `json_load`/`json_save` on kernel, `tcp_*`,
`http_get`,
passing modules into expressions/calls/indexing, `print`/`str` of
user-declared Funcs (builtins work as values, shown as `<builtin str>`)

`m = mod` / `m = pkg.sub` may alias (zero runtime cost,
`m.attr` behaves exactly the same including `print m`) - but never pass a module into a
function/operator/index (a name assigned over the alias becomes a normal value)

hosted (`xbuild`) additionally has: `argv()` (List of argv[1:]), `input()`
(one line, bare EOF = error), `env(name)` (missing = null),
`open(path, "r"/"w")` -> File (displays `<file PATH>`), `read(f)` whole file,
`write(f, s)` (returns byte count), `close(f)` (double close = no-op) -
errors are `errno N` (interp shows strerror),
`json_load`/`json_save` (file read/write through the File runtime),
`scall(nr, a1..a6)` - raw `syscall` (used to write
user programs that talk to our kernel, e.g. `kernel/uush.holy`) but
`xkernel` does not have it, because in ring 0 a `syscall` followed by
`sysret` would drop to ring 3 the wrong way

## Traps to remember

- `/` truncates like C (hosted yields Float)
- Str index/slice/split count **bytes** (non-ASCII differs from interp)
- `split` with an empty sep raises (interp/native crash instead)
- Division by zero on kernel is a HW `#DE` (halt), not a catchable error
- Reading a never-assigned variable = `unknown variable` error (not garbage)
- `and`/`or` do **not short-circuit** - both sides always run, so write bound checks
  as separate calls (`js_at(s, i, n)` in `runtime/json.holy`) or an out-of-range
  `s[i]` will raise
- `json_*` is compiled from `runtime/json.holy` (a private `<json>` module that
  x64gen embeds in the image when the program calls it) - it is not an API:
  you can `import` it yourself if the repo is on HSPATH, but anything needing
  `type_name` (a private hook) will not compile

## Pass / fail examples

```hs
for i in range(3):
  print i
# => 0
# => 1
# => 2
print "ab"[1:]
# => b
print [3][0:]
# => [3]
```

```hs-norun
print 1.5 + 2.5  # Float: 4.0
import os        # no such module: cannot find module
print argv()     # argv: not in x64 subset
```

## Runaway recursion

Every backend reports `error: stack overflow (recursion too deep)` (exit 1):
interp through its recursion limit, native through a SIGSEGV handler, x64
through a SIGSEGV handler (rt_sigaction + sigaltstack at _start; zero
per-call cost, compares rsp against 7MB of used stack; a smaller `ulimit -s`
still segfaults)
