# AGENTS.md — holyshit (hs) v0.6.10 language reference for AI coding agents

Read this file before writing or fixing `.hs` code. It is the complete
working reference. Longer prose lives in `docs/` (`docs/index.md` is the
map); `SPEC-v1.md` has design rationale; this file has rules.

## Run

```sh
python3 interp.py prog.hs [args...]        # run now (reference behavior)
python3 hs.py check prog.hs                # syntax+scope only, no output binary
python3 hs.py build prog.hs [-o prog]      # native binary
python3 hs.py run prog.hs [args...]        # build to temp and run
python3 hs.py fmt prog.hs [-w|--check]     # canonical 2-space (--check ignores comments)
python3 hs.py xbuild prog.hs [-o prog]     # x86-64 machine code, no gcc (subset)
python3 hs.py xkernel prog.hs -o k.elf     # freestanding kernel, no gcc/as/ld
python3 hs.py lsp                          # language server (stdio, no deps)
python3 interp.py --json prog.hs           # errors as {"file","line","message"} on stderr
python3 hs.py --json check|build ...       # same JSON error contract
```

Both backends print byte-identical stdout. If they differ, the NATIVE side
is usually right about nothing — file a bug, don't work around it.

## Tooling you can call instead of guessing

```sh
python3 scripts/lsp_client.py --diag prog.hs          # errors + lines (no server hang)
python3 scripts/lsp_client.py --symbols prog.hs       # every def/var/import in a file
python3 scripts/lsp_client.py --hover prog.hs 3 5     # builtin sig, keyword, or variable
python3 scripts/lsp_client.py --def prog.hs 2 10      # jump to definition (cross-file)
python3 scripts/lsp_client.py --refs prog.hs 2 10     # every use of that name
python3 scripts/lsp_client.py --sig prog.hs 4 9       # signature of the call in progress
python3 scripts/lsp_client.py --wsym prog.hs name    # search symbols project-wide
python3 scripts/lsp_client.py --complete prog.hs 1 4  # keyword + builtin + local names
python3 scripts/lsp_client.py --format prog.hs --write
python3 scripts/gen_api.py                            # regenerate docs/api.json
python3 scripts/gen_errors.py                         # regenerate docs/errors.md
```

`docs/errors.md` lists every error message in the language (auto-extracted from
the sources) — look a message up there when a program fails.
`docs/api.json` holds every builtin (signature + backends) in machine form.
`scripts/lang_data.py` is the single source both the LSP and `tests/test_docs.py`
read — keep it in sync with `interp.BUILTINS` or the docs test fails.
Editor configs (VS Code / Neovim / Helix / Zed) live in `editors/`.

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
- `& | ^ << >>` and `~x` are **bitwise, Int only** (Bool is not an Int), shift
  count must be 0..63, `>>` is arithmetic. Bitwise binds tighter than `+ -`
  and looser than `* / %`. x64 Int is 62-bit signed, so bit 61 is the sign
  bit: `1 << 61` is negative there and positive on interp.
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
`e` is a Str `"msg at line N"`. `finally` runs on every exit — including when
the `except` handler itself raises (all backends: interp, gcc, x64, kernel).
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
- `load8/load32/load64/store8/store32/store64`, `alloc(n)` (zeroed, GC'd, no free).
  `load64`/`store64` are raw untagged 64-bit access -- what the kernel uses to
  read/write page-table entries and pointers.
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
Memory (all backends): `read_mem(ptr, n)` — n raw bytes at an address as Str
(byte-preserving: NUL and high bytes included; the kernel reads bootloader
structs and ramdisk images through it)
JSON: `json_parse json_str json_load json_save`
Process: `argv()→List` (no prog name) `env(name)→Str|Null` `system(cmd)→Int status`
Net (http only): `tcp_connect/send/recv/close tcp_listen/accept http_get(url)→body`
Kernel-surface (xkernel freestanding): `ticks readkey pmm_alloc pmm_total pmm_free`
(`pmm_*` is the legacy bump allocator; real code uses `kpmm`), `mb_info`/`mb_magic`
(bootloader info), `image_end` (first address after the kernel image),
`cr2`/`cr3`/`set_cr3`, `invlpg(v)`/`tlb_flush()`,
`ctx_swap(save, load)`/`task_run(sched, task)`/`task_init(ctx, top, func)`,
`irq_off()`/`irq_on()`, `sched_on_tick(f)`/`sched_tick_clear()`
(tasks + preemption; ctx block 136B: all 15 GPRs + rsp + rip),
`syscall_register(f)`/`user_stop()`/`enter_user(rip, frame)` (ring 3: `f` gets
`(nr, a1..a6)` as tagged hs Ints and returns the raw result; `user_stop`
ends the user back in the `enter_user` caller; user code is any `xbuild` ELF
loaded as a multiboot module — the hosted numbers write=1, mmap=9, exit=60
work with no extra runtime), `exec_enter(rip, frame)` (same `iretq` but records
no continuation — `exec` over a live image)
(+ unsafe alloc/load/store/as_*)

x64 hosted only: `scall(nr, a1..a6)` — raw `syscall` with Ints for arguments
(what user programs use to reach the kernel; rejected in `xkernel` because a
ring-0 `syscall` would `sysret` into ring 3).

### x64 backend subset (`hs.py xbuild` / `xkernel`)

Has: Int (62-bit), Str values (literals, `+` concat, `len`, `==`, `<`,
slicing `s[a:b]` byte-based, `split`/`find`/`join`),
List values (literals, `+` concat, `len`, `append`, `==`, indexing incl.
negative, `l[i] = v`, slicing `l[a:b]`, `range()` materializes a List), Bool, `null`,
`not/and/or`, `if/elif/else`, `while`, `for` (`for i in range([a,] b)` lowers to a
counter loop; `for x in <str|list>` yields elements), `break`/`continue`,
`def` (recursion + closures), `try`/`except`/`finally`/`raise` (full interp
parity incl. dynamic messages with line numbers; `except as e` binds
`"msg at line N"`; bare `raise` re-raises lexically; setjmp/longjmp over a
fixed 256-frame handler stack), `import` (real file or dotted package; module
body runs once via guarded init, parent-first; `mod.attr` read + write,
`print mod` → `<module name>`; HSPATH + program-dir lookup; circular imports
are a compile error), `global` (module/function globals from functions),
`str()` (incl. lists → `[1, x]`), `int()`,
`len()`, `print` (lists print as `[a, b]`, nested), `unsafe:` I64/U64/Ptr +
structs, kernel builtins above.

Missing (compile error, on purpose): Float, Dict,
attribute access on values (only modules have attrs), `extern`,
`scall`/`enter_user`/`exec_enter`/`user_stop` are hosted-only.
Modules are compile-time only: passing a module as a
value (`f = mymod`, `x = pkg.mod`) is an error — use `mod.attr`. `/` truncates
like C here, not hs. Out-of-range indexing reports `index out of range`.

Errors: every dynamic failure carries `message at line N` (uncaught prints
`error: message at line N`, exit 1) — operator/index/len/call messages name
the runtime types, unknown reads report `unknown variable 'x'`; exotic combos
(Str vs Func compare, `str(func)`) fall back to generic `type error`. Locals
start UNBOUND; call arity is checked at every user call, at registration
for task/tick/syscall handlers (exact interp message with the callee's own
name, catchable by try). Freestanding integer
divide hits hardware #DE (`EXC 0`, halt) instead of a catchable error.
Str index/slice/split are byte-based (non-ASCII diverges from interp);
`split` with empty separator raises (interp/native crash instead).

Value representation: low 2 bits are the tag — `01` Int (`v<<2|1`),
`10` Bool (0x02/0x0A), `11` Null (0x03)/Unbound (0x0B), `00` heap object
(`[kind][len][bytes]` for Str, `[kind][code][nparams][name][caps]` for
Func — nparams/name let every call check arity). Heap = bump
allocator, never frees. Type errors print `type error` and exit(1)/halt.

Inside `unsafe:` values stay raw machine words (literals untagged);
use `as_ptr(x)` / `as_int(x)` to cross from tagged dynamic values.

Crossing the boundary (x64):
- safe -> unsafe: pass a **tagged Int**; `as_ptr(n)` yields a raw pointer.
  `as_ptr(s)` on a Str/Func yields its heap address (payload at +16);
  interp/native reject this (their values have no addresses) — kernel-only.
- unsafe -> safe: `return <raw>` and `as_int(p)` re-box into a tagged Int, so
  the value can be printed/compared outside `unsafe:`.
- a `return` inside `unsafe:` always boxes as **Int**: return Bool/Null at safe
  level instead (`0 == false` is cross-type false).
- x64 resolves module-level names statically: define a helper **before** its
  callers in the file, or the build fails with `unknown variable`.
- `unsafe:` bodies may only call `alloc`/`load*`/`store*`/`as_*` (no other
  calls, not even module helpers): compute addresses outside, pass them in.
- a raw pointer parked in a safe variable is NOT printable (its low bits read
  as a heap tag): convert with `as_int` first.

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
5. Touching a builtin list, an error message, or a doc example? Run
   `scripts/gen_api.py` / `scripts/gen_errors.py` then `tests/test_docs.py`
   — it fails loudly on drift.
6. Lost? `python3 scripts/lsp_client.py --diag prog.hs` gives the same error
   with a 0-based line, no rebuild needed.
