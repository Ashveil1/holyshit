# holyshit - SPEC v1.0 (new language: dynamic + indent + native target)

> Status: v0.6.30 - language + 4 backends (interp / native gcc / direct x86-64 /
> freestanding kernel) + middle IR + stdlib + formatter + language server + test-checked docs
> Principles: easier to write than Python, run immediately in a JIT workflow, fully
> dynamic core, low-level work lives only in `unsafe`, syntax may break from v0.3 (v0.3 kept as legacy)

## 1. Lexical

- Indentation is meaningful like Python: a block starts after a line ending in `:`
- Indent must be consistent within a block (2 or 4 spaces recommended, no leading tabs)
- Script files use the `.hs` extension, run with `python3 interp.py prog.hs`
- Blocks (if/while/for) do not create scopes - only functions create scopes (like Python)
- A statement ends at the newline (`;` no longer works)
- Comments: `#` and `//` to end of line
- Strings: `"..."` with escapes `\n \t \r \0 \" \\` (unknown escapes
  pass through as literal characters); no multi-line strings in v1
- Floats may use exponent notation: `1.5e3`, `2.5E-2`, `1e3`, `.5e1` (and `hs fmt`
  preserves the original form)

## 2. Values (all dynamic, no type declarations)

| Type | Example | Notes |
|---|---|---|
| Int | `42`, `-7`, `0xFF` | 64-bit signed |
| Float | `3.14`, `2.0`, `1.5e3` | 64-bit; repr is shortest round-trip
matching `print`/`str` in Python (`0.1` not `0.10000000000000001`) |
| Str | `"hello"` | UTF-8, concatenate with `+` |
| Bool | `true`, `false` | |
| Null | `null` | An unassigned var is not Null by default - you must assign before use |
| List | `[1, 2, "x"]` | holds mixed types, `a[i]`, `a[i] = v` |
| Dict | `{"k": 1}` | keys are Str only in v1 |
| Func | made by `def` | first-class: pass as arg / return from func |

- `+` works on Int+Int, Float+Float (mixed Int+Float -> Float), Str+Str (concatenation)
- `- * / %` work on numbers (`/` always divides as Float, division by 0 = error)
- `//` does not exist as an operator - `//` starts a full-line comment (like `#`)
- `pass` = empty statement (for blocks not yet written)
- Comparison: `== != < > <= >=` on same types (Str compares lexicographically)
- Logic: `and or not` (short-circuit except on the x64 backend), truthiness: `false null 0 "" [] {}` are false, everything else true
- A runtime type error (e.g. `1 + "a"`) = runtime error with the offending line

## 3. Variables and functions

```
x = 10            # create/update a var, no declaration
x = x + 1

def fib(n):       # def name(params):
  if n < 2:       # block via indent
    return n
  return fib(n - 1) + fib(n - 2)

print fib(10)     # called with parens; 0-arg calls may drop the parens
```

- `return expr` / `return` (yields Null)
- Scope: local inside func, global outside; a func may read globals, writing a global needs `global x` first (like Python)
- recursion works, closures work (value snapshot at `def` time - copy semantics;
  interp shares the env, native copies; self-recursion works, mutual recursion between
  nested funcs does not yet; the kernel forbids closures, use globals)

## 4. Control flow

```
if x > 0:
  print "pos"
elif x < 0:
  print "neg"
else:
  print "zero"

while n > 0:
  n = n - 1

for i in range(5):       # 0..4
  print i
for x in [10, 20]:
  print x
for k in {"a": 1}:       # iterates keys
  print k
```

- `break` / `continue` in while/for
- `range(n)` = 0..n-1, `range(a, b)` = a..b-1 (the old `0..5` is removed, use range)
- `for i in range(a, b, s)` (s may be negative): parse-time desugar to `range(0, N)` + `i = a + k*s`; a,b,s are evaluated once; s == 0 = division by zero; only usable in `for`

## 5. First builtins (v1)

- `print a, b, ...` -> space-separated + newline (like v0.3); bare `print` = empty line
- `len(x)` -> length of Str/List/Dict
- `range(n)`, `range(a, b)`
- `str(x)`, `int(x)`, `float(x)` conversions (failed conversion = error)
- `input()` reads 1 line from stdin -> Str
- File (the smallest useful set): `open(path, mode)` + `read(f)` + `write(f, s)` + `close(f)` with mode `"r"`/`"w"`
- `len` on a Dict = number of keys
- **Dict keys (v0.7):** keys are `Str` or `Int` (Bool/Float/others raise `dict key must be Str or Int`; Bool is refused because `true == 1`). `{1: "a", "k": 2}`, `d[5] = x`. `json_str` still requires Str keys. All backends (interp/IR/native/x64) agree; this also fixed the x64 dict `==` bug that used to always answer true.
- String/List: `append(a, x)`, `split(s)` / `split(s, sep)`, `find(s, sub)` (-1 when absent),
- **Method sugar (v0.7):** `x.append(v)`, `s.split(sep)`, `s.find(sub)`, `sep.join(list)` can be written
  as methods, desugared at parse time to `append(x, v)` etc.; every backend sees an ordinary builtin call
  (the formatter keeps the method form). If the receiver is a path starting with an `import`ed module
  (`std.heap.find(...)`) it still means the module function as before.
  `join(sep, list)`, slice `s[a:b]` / `s[:b]` / `s[a:]` (lists too, negative indexes ok)
- **lambda (v0.7):** `lambda x, y: expr` (no multi-line body) desugars at parse time to a hoisted `def _lamN` before the statement. The formatter prints it back as `lambda`.
- **f-string (v0.7):** `f"x={x}, sum={a + b}"` desugars at parse time to `"x=" + str(x) + ...`; `{{` `}}` are literal braces; a string literal containing `"` is not allowed inside `{}`. The formatter keeps the f-string form.
- **class (v0.7):** `class C:` + `def`s taking `self` as the first param, `__init__` is the constructor. Parse-time desugar: each method becomes a function `C__m`; `C(args)` is a function that builds the dict `{"m": C__m, ...}` then calls `__init__`; `o.f` = `o["f"]`, `o.f = v` = `o["f"] = v`, `o.m(x)` = `o["m"](o, x)`. Single inheritance `class D(B):` (copies B's method table first, then overrides; `__init__` is inherited if not written; call the parent's init with `B__init__(self, ...)`; B must be declared first). Limitations: no super()/multiple inheritance; method names must not clash with builtin sugar (`split find join append`); the receiver of `o.m()` must be a name or a field (`a.b.m()` works, `f().m()` does not - store it in a variable first); `x = some_module` stays a module (per the imported module name). Printing an object shows its method dict too.
- Process: `argv()` -> List of args (excluding the program name), `env(name)` -> Str/Null,
  `system(cmd)` -> Int exit status (through the shell)
- Net (http only, no https): `tcp_connect(host, port)` + `tcp_send/recv/close`,
  `tcp_listen(port)` + `tcp_accept`, `http_get(url)` -> body of a 2xx (others error)
- JSON: `json_parse(s)` <-> `json_str(x)` (deeper than 200 levels = error)
- Agent kit: `read_text/write_text/append_text` (whole files), `exists/ls/mkdir`,
  `json_load/json_save` (direct JSON files); every error has a `--json` mode for agents to parse
- Memory: `read_mem(ptr, nbytes)` -> a Str of the `nbytes` raw bytes at address `ptr`
  (byte-preserving: NUL and high bytes survive, unlike UTF-8 decode) - needed for
  structures the allocator does not own (boot info, ramdisk) and the only one that
  works on every backend including the kernel
- None of these work in the kernel (explicitly banned) except `ticks/readkey/pmm_alloc/meminfo`
  which have kernel-side approximations, and `read_mem` which truly works

## 5.1 Modules and stdlib

- `import mod` / `import pkg.mod` (dotted becomes a path; searched in the program's dir first,
  then `HSPATH` (colon-separated), then cwd)
- A parent with no file is an automatic empty package; initialized once; circular = runtime error
- Attribute access works across every level (`std.str.trim(...)`); re-`import`ing the same module is fine
- `std/` ships with the language: `std.str` (trim/pad/starts_with/ends_with/lines),
  `std.list` (map/filter/fold/any/all), `std.heap` (heap_init/malloc/free,
  heap_free/heap_nblocks - a free-list allocator written in hs+struct itself)

## 6. Errors

- `try:` / [`except:` [`as e`]] / [`finally:`] (at least one of except/finally required)
  `e` is a string `"msg at line N"`; nested try + `break/continue/return` inside are supported
  (native uses setjmp/longjmp, C locals are volatile only in funcs containing try)
  `finally` runs on every way out on both backends (including return/break/continue and propagating errors)
- `raise "msg"` throws your own error (must be a Str); bare `raise` = re-throw inside `except`
  (native uses a lexical frame - it cannot cross a function boundary, interp can)
- An error with no try stops the program immediately, printing `error: <reason> at line N`

## 7. `unsafe` (static subset for low-level work - done, phase 4a)

Inside an `unsafe:` block is another, static language. Its rules differ from the dynamic core:

- **Three types**: `I64` (signed 64), `U64` (unsigned 64), `Ptr` (byte pointer)
  plus struct pointers `Name*` (see below)
- **Forbidden**: float, string, list, dict, `def`, `for`, calling dynamic functions
  (`print` works; string literals work only with `print`)
- **Memory**: `Ptr p = alloc(n)` gives n bytes of zeroed memory (GC frees it, no manual free)
  `*p` / `*p = v` read/write 64-bit (must be 8-aligned, else error),
  `load8/load32/store8/store32` access any byte width
- **Pointers**: `p + n` / `p - n` step in bytes, `p - q` is a distance, `==`/`!=` allowed, `< >` forbidden
  `as_ptr(int)` turns a number into an address (for MMIO, e.g. `as_ptr(753664)`),
  `as_int(p)` converts back, `null` is address 0
  (all of these accept struct pointers - a struct always decays to an address)
- **structs** (direct hardware/driver layouts):
  ```
  unsafe:
    struct Desc:
      U64 low
      U64 high
      U64 entries[512]
      Node* next        # points at another struct (declared earlier) / self-ref ok
    Desc* d = alloc(sizeof(Desc))   # sizeof works on structs and I64/U64/Ptr (=8)
    d.low = 4660
    d.entries[3] = 22
    print d.low
  ```
  - Fields are only `I64/U64/Ptr/Struct*` (+ fixed arrays `[N]`); every field is 8 bytes, no padding
  - `p + n` / `p - n` step by `sizeof` (C semantics); `p - q` (same struct) = element count
  - `p.field` / `p.arr[i]` read, `p.field = v` writes - with bounds check + null check
    On native, all are volatile accesses (MMIO-safe)
  - `as_int(p)` / `load/store*` accept struct pointers directly
  - A struct is a program-level name (redeclaring the same layout is ok, different = error),
    bound to one build (does not cross test/run files in the same process)
  - Not yet: nested structs by value (pointers only), bitfields, unions, `->` (use `.`)
- Blocks nested in `unsafe:` (`if`/`while` inside) keep the static rules
  at both parse and runtime (no dynamic leaks in)
- Writing a global from inside a func needs `global` (the Python rule applies to unsafe too)
- **strict**: never mix `I64` with `U64` (same error message on both backends),
  number literals adapt to context, `/` and `%` truncate like C (unlike safe `/` which yields Float)
- **`and/or/not` in unsafe return I64 0/1** (not the operand like safe code)
- **`asm("...")`**: drops raw assembly into the binary (only with `hs.py build`; the interpreter errors clearly)
- **Every load/store is volatile** in the generated C - safe for MMIO
- **Dynamic bridge**: reading a dynamic var inside unsafe = unbox to I64 with a type check (wrong type errors),
  writing a value out of unsafe = auto-box (a `U64` beyond 63 bits errors when boxed)
- **scope**: unsafe vars live in the function (or global when outside a func), zero-init,
  cannot be captured across functions (compile error), cannot be `global`
- Extra reserved names (cannot be used as var/func): `import module try except`

Example (touching simulated "hardware"):
```
unsafe:
  Ptr uart = as_ptr(1016)   # really an MMIO address
  store8(uart, 72)          # write one byte
  print load8(uart)         # read it back
```

Still missing (needs a freestanding runtime + boot before it is a real kernel):
cannot run on bare metal - the binary still depends on the OS's libc/GC

## 8. Example program (must run after phase 2)

```
# fib + file
def fib(n):
  if n < 2:
    return n
  return fib(n - 1) + fib(n - 2)

print "fib:", fib(10)

f = open("out.txt", "w")
write(f, str(fib(15)))
close(f)
```

## 9. Notes for the interpreter implementer (phase 2)

- value = a tagged union in Python (dict/tuple) for now; do not think about performance
- Start with a plain tree-walk over the AST; no optimization of any kind in phase 2
- Minimal test set: recursive fib, while sum, for+range, list/dict, file write/read back, type errors must carry line numbers

## 10. Native backend (phase 3 - 3a done, 3b remaining)

- 3a (done, `hs.py` + `native/rt.{h,c}`): AST from `interp.py` -> C -> `gcc -O2 -lgc` into a native binary
  (`hs.py build prog.hs [-o prog]`, `hs.py run prog.hs` = build to temp then run immediately)
- value = tagged `Val` (16 bytes), memory uses Boehm GC - no refcount bookkeeping
- fib(22): interpreter 0.85s -> native 0.009s (~95x), 35KB binary
- Limitation lifted: closures work (copy semantics via `v_func_setcaps` + `hs_cur_caps`);
  only mutual recursion between nested funcs remains (use globals instead)
- Tooling: `hs.py check` (parse+scope without gcc), `--version`, `run` forwards args,
  `VERSION` + `.gitignore` + `README.md` + `legacy/` (from v0.3)
- 3b (done): the `import` module system (init once, circular = runtime error),
  `m.attr`/`m.attr=` (exact static + dynamic through a registry), `v_slice`, builtins
  `append/split/find/join`, `try/except[as]` (setjmp, volatile only in funcs with try)
- `tests/test_native.py`: **17/17 pass**, matching the interpreter character for character including errors + line numbers
  (`mod_*` are helpers, not built directly; `uasm` is native-only)
- Remaining: `for` without materializing the seq, a real hash dict (old item)

## 11. `extern` - using things from other languages (C ABI = the universal medium)

```
extern:                       # libc (default)
  I64 puts(Str s)
  U64 strlen(Str s)
  Ptr malloc(U64 n)
  U0 free(Ptr p)

extern from "m":              # -lm (a bare name = -l, a / = path, .c = compiled+linked for you)
  F64 sin(F64 x)

extern from "helper.c":       # C source (e.g. a kernel part written in C) - built for you
  I64 hs_add3(I64 a, I64 b, I64 c)
```

- Boundary types: `U0` (void, return-only), `I64 U64 F64 Str Ptr`
  `Str` = `char*` (NUL-terminated), `Ptr` = an address as a dynamic-side Int
- Callable from safe code only (forbidden in `unsafe`, forbidden in the kernel - the kernel has no libc)
- native emits no prototype but `dlsym`s directly (`-rdynamic -ldl`), so libc function names never clash
- interp runs through `ctypes` (including `.c` files compiled into a temporary .so); results match native character for character
- struct by pointer works: `malloc` then `store*/load*` in `unsafe:` at offsets (tests/t_ffistruct.hs uses `gmtime_r` filling `struct tm`) - only programs with `extern` may load/store real C addresses (interp uses ctypes); without extern it stays a bounds-checked simulated arena
- Not possible: struct by value, callbacks, variadics (e.g. `printf` directly) - write a C wrapper
- A different language = only a different origin: Rust/Zig/C++/Go(cgo) exporting the C ABI can all be
  `from`ed as `.so`/`.a`/`.o`; C source from the kernel can be linked directly like `helper.c` above

## 12. Kernel (pure xkernel freestanding - the gcc line is deleted)

- History: phase 5a used gcc/as/ld + krt.c (a C runtime) - all deleted once xkernel
  covered the behavior fully (see git history). The kernel now comes from `.hs` + the encoder alone
- `kernel/` holds only `.hs` (xdemo/kx2/kxexc_*); `tests/test_xkernel.py` **18/18**
  (boot, fib, timer ~200 ticks, keyboard, PMM 32768/-3, EXC 14/0)
- kernel runtime = hs subset + asm in `x64gen.py` (serial, bump heap, IDT/PIC/PIT,
  ticks/readkey/pmm) - no C left in the kernel line at all

## 13. Direct x86-64 backend (phase 6a - hosted subset, no gcc/as/ld/libc)

- `x64.py`: a self-written assembler + static ELF64 writer (REX/ModRM/SIB, rel32/rip-rel,
  2 segments RX+RW, entry `_start`)
- `x64gen.py`: hs subset -> machine code; the runtime is written as pure machine code

  (print_int/fmt_int, bump malloc over mmap, type_err, divzero, `_start`+exit) -
  all assembled from instructions written by our own encoder
- **Tagged values (v2)**: low 2 bits = tag - `01` Int (62-bit payload, `v<<2|1`),
  `10` Bool (0x02 false / 0x0A true), `11` Null 0x03 / Unbound 0x0B, `00` heap object
  (`[kind][len][bytes]` = Str, `[kind][code][caps...]` = Func,
  `[kind][len][cap][buf]` = List) -> Str/Bool/Null/List are full values,
  not just ints; `print` picks from the tag, a type error = `type error` + exit(1)/halt
- value-side runtime: `x_str_at` (build a Str from rodata), `x_str_cat`, `x_str_cmp`
  (used by both `==`/`!=` and `<`/`>`), `x_str` (including List -> `[1, x]` via `x_list_str`),
  `x_num_to_str`, `x_len` (Str/List), `x_truth`, `print_val` (+ `x_print_list`
  printing nested `[a, b]`), `x_eq` (+ `x_list_eq` deep compare), `x_cmp`,
  `x_slice`, `x_split1/2`, `x_find`, `x_join` and the 256-byte whitespace table -
  all assembled from instructions written by our own encoder
- subset: Int, Str (literals as values, `+` concatenation, `len`, repetition comparisons,
  byte-based slicing `s[a:b]`, `split`/`find`/`join`),
  List (`[..]`, `+` concatenation, `len`, `append` (header stays in place, only buf grows -
  aliases see the same), `==` deep compare, `l[i]`/`l[-1]`/`l[i] = v`, `range()` returns a real
  List, `for x in <list>`), Bool, null, not/and/or (returns the operand per hs),
  if/elif/else, while, `for` (`for i in range([a,] b)` lowers to a counter loop;
  `for c in <str>` yields one-character Strs), break/continue (works in nested while/for),
  def/call/recursion/closure (caps through r15),
  `import` (real file or dotted package; the body runs once through a guarded parent-first
  init; read/write `mod.attr`, `print mod` -> `<module name>`;
  files found via program-dir + HSPATH; circular = compile error),
  `global` (a function may modify its own module's globals), `str()` (including List),
  `int()`/`len()`, `print` (nested Lists ok), unsafe I64/U64/Ptr + struct;
  `/` truncates like C; out-of-range index = `index out of range`;
  modules are compile-time only (a module cannot be passed as a value - use `mod.attr`)
- full exceptions (`try`/`except`/`finally`/`raise`): a self-written setjmp/longjmp
  over a fixed 256-frame handler stack (no libc); every error carries message + line
  matching interp (`cannot add Int and Str`, `unknown variable 'x'`, `not callable`,
  `len of`, `not iterable` etc. via `x_tname` + string builders);
  `except as e` binds `"msg at line N"`, bare `raise` re-raises lexically;
  `break`/`continue`/`return` in try run finally + pop the handler correctly;
  uncaught prints `error: msg at line N` exit 1; reads of never-assigned names become
  UNBOUND and error on read (not stack garbage)
- runtime: bump allocator over a 16MB mmap arena (16-aligned, never freed - like the kernel heap),
  arena grows automatically when full, an `alloc` larger than 16MB gets its own arena
- Measured on an i7-6700HQ (TSC 2592MHz): fib(25) ~0.007-0.012s (gcc-Val 0.021s, interp 3.79s),
  (was 0.005s before adding error-check + unbound-check everywhere - the price of diagnostics),
  4KB binary vs 77KB; timer-IRQ latency (SIGALRM, `scripts/irq_lat.py`):
  @2ms med 2000us p99 +100us max +116us, @500us p99 +37us max +70us
  (these numbers are a shared Linux laptop, not bare metal - bare metal should be ~1-5us)
  (fib rose from 0.003s to 0.005s after tagged arithmetic - the price of representation)
- Not yet: Float/Dict, extern, attrs on values (only modules have attrs),
  argv, `split`/`find`/`join`, `asm()` (does not work with our own encoder) -
  all are clear compile errors
- Inside `unsafe:` values stay raw machine words (literals are not tagged) - use `as_ptr(x)` /
  `as_int(x)` as the bridge from dynamic values
- `hs.py xbuild prog.hs [-o prog]` / `hs.py xrun prog.hs`, tests `tests/test_x64.py`
  (**25/25**: + slice, textops, err_slice_idx/obj, err_split/join;
  `mod_*` = helper, not run directly)

## 14. Freestanding kernel with the x64 backend alone (phase 6b - no gcc/as/ld)

- `hs.py xkernel prog.hs -o k.elf`: 32-bit encoder (`Asm32`) + trampoline
  (cli -> cr3/cr4/EFER/cr0 -> lgdt -> far jmp) + page-table prefill in Python
  (1GB identity) + 64-bit payload + ELF32 writer - the result boots in QEMU for real
- freestanding runtime: serial COM1, a fixed 16MB bump heap at 32MB, halt,
  IDT 48 gates + PIC remap + PIT 100Hz + keyboard scancode map, `ticks/readkey/pmm_*`,
  the same tagged values as hosted (Str/Bool/Null/List really work on bare metal)
- `finally` runs on every way out including an **error raised inside the `except` of the
  same try** - both native (`hs.py build`) and x64 (`hs_try_push0` nested as a second
  handler layer then `hs_reraise`) match interp; regression tests in
  `tests/t_finally.hs`, `tests/x64/try.hs`, `kernel/ktry.hs`
- `kernel/xdemo.hs`, `kx2.hs` (timer/keyboard/PMM), `kxstr.hs` (Str over serial),
  `kxlist.hs` (List: literal/append/index/`==`/`for`/`str()` over serial),
  `kimp.hs`+`kmod_h.hs` (import + `mod.attr` on bare metal),
  `kxexc_pf/de.hs` (EXC 14 / EXC 0), `ktry.hs` (try/except/finally/raise over serial)
  `kxslice.hs` (slicing + split/find/join over serial)
  + `tests/test_xkernel.py`: **62/62 pass**
- Remaining: dynamic paging (map/unmap pages), frame allocator + `std.heap` in the kernel,
  scheduler, filesystem, user mode

## 15. Docs + tooling (phase 7 - v0.5.0 -> v0.6.0)

This phase's goal: **every person and every AI can write this language** - the docs must
not lie (every example must really run) and the editor must help with no dependencies

### 15.1 One data layer (single source of truth)

- `scripts/lang_data.py` - keywords (28) + builtins (48) with signatures,
  descriptions, and the set of supporting backends (`interp`/`native`/`xbuild`/`xkernel`)
- `interp.BUILTINS` remains the runtime truth - `tests/test_docs.py`
  confirms the table covers every one and has no strays (`pmm_total`/`pmm_free`
  are freestanding, hence the only allowed extras)
- `scripts/gen_api.py` reads those two sources and writes `docs/api.json`
  (machine-readable) + `docs/builtins.md` (a markdown table) - regenerable
  with one command, and the test fails if the files drift from the generator
- `scripts/gen_errors.py` pulls every `HSErr(...)` from `interp.py`/`hs.py`/
  `x64gen.py`/`fmt.py` via AST and writes `docs/errors.md` (351 messages)
  with a "common errors" table - AI can grep causes directly

### 15.2 Docs

| File | For |
|---|---|
| `docs/index.md` | starting point + topic table |
| `docs/tutorial.md` | first program in 10 minutes (every block really runs) |
| `examples/` | 8 example files covering the language + `.expected` for each |
| `docs/stdlib.md` | `std.str` / `std.list` / `std.heap` |
| `docs/x64-subset.md` | scope + traps of the gcc-free backend |
| `docs/kernel.md` | the freestanding kernel |
| `docs/cheatsheet.md` | the whole language on one page |
| `docs/errors.md` | every error message (generated from source) |
| `docs/lsp.md` | language server + editor hookup |
| `docs/for-agents.md` | shortcuts + tools for AI |
| `AGENTS.md` | compact rules (the agent's main reference) |
| `CONTRIBUTING.md` | rules/steps for extending the language |
| `SPEC-v1.md` | design rationale (this file) |

`tests/test_examples.py` (**17/17**) requires every `examples/*.hs`
to really run (interp) and match native (gcc) - a broken example turns the
test red, and it found 2 real parity bugs (see §15.2 history)

`tests/test_docs.py` (**38/38**) runs every ```hs block in `docs/*.md` against
the `# =>` lines in order, checks drift of `api.json`/`builtins.md`, checks that
every link in README/`docs/index.md`/`AGENTS.md` points at a real file, and runs the
commands in `docs/lsp.md` for real - so the docs break with the code

### 15.3 Language server (`lsp.py`)

- stdio + JSON-RPC written in pure stdlib (no pip dependency), entered via
  `python3 hs.py lsp` or `python3 lsp.py`
- Features: `textDocument/publishDiagnostics` (parse + scope check on every
  edit/save), `hover` (builtins with backends, keywords, def/param/vars,
  `mod.attr` pointing at the defining file), `completion` (keywords + builtins + in-file
  names, and only a module's top-level names after `mod.`), `definition`,
  `references` (cross-file within the same directory + `HSPATH`),
  `documentHighlight`, `signatureHelp` (user + builtin, with activeParameter),
  `documentSymbol`, `workspace/symbol`, `formatting` (calls `fmt.py`)
- Positions use UTF-16 code units per the LSP spec (Thai/emoji do not shift)
- `scripts/lsp_client.py` is a one-shot client so agents can call it without
  keeping a server alive (`--diag/--hover/--def/--complete/--symbols/--format`)
- `tests/test_lsp.py` (**25/25**) fires the real protocol through a pipe

### 15.4 Editors

`editors/vscode` (client.js, no npm install), `editors/neovim`
(syntax/vim + `lua/holyshit.lua`), `editors/helix`, `editors/zed` -
all point at the same `python3 <repo>/lsp.py` command

### 15.5 The formatter as a real gate

`hs fmt --check` compares only "structure" (ignoring comments and blank lines,
because the printer cannot print comments - the lexer already dropped them) and the flag
parsing now accepts both `fmt f.hs --check` and `fmt --check f.hs`. The whole repo is
canonical now, and `tests/test_fmt.py` re-checks the whole repo (except
`tests/fmt/*.hs` which are intentionally non-canonical) - format before editing
and the test goes red if anything drifts

### 15.6 v0.6.0 - wider LSP + generatable docs

- `resolve_parts()` in `lsp.py` is the single resolver for dotted names
  (hover/definition/completion/references/highlight/signature all share it)
- Added `references` (cross-file), `documentHighlight`, `signatureHelp`,
  `workspace/symbol`, completion after `mod.`, hover on `mod.attr` pointing at the file
- 2 parity bugs the new examples exposed: `finally` was skipped when the `except` handler
  raised - fixed in both native (`hs.py`) and x64/kernel (`x64gen.py`)
- `docs/errors.md` generated from source AST (351 messages)
- `tests/test_examples.py` forces every example file to really run
- `hs fmt --check` works for real (structural compare, comments ignored) and the whole
  repo must be canonical

### 15.7 Test status after phase 7

`test.py` 38 · `test_native.py` 39 · `test_fmt.py` 4 · `test_x64.py` 28 ·
`test_xkernel.py` 99 · `test_examples.py` 17 · `test_lsp.py` 25 ·
`test_docs.py` 38 (run everything: `python3 tests/run_all.py`)

### 15.8 OS prep: `load64`/`store64` (v0.6.1)

The base of OS work is reading/writing 64-bit page-table entries from `.hs` - until
then `unsafe:` had only `load8/load32/store8/store32`, which cut 64-bit values in half

- `load64(p)` / `store64(p, v)` in `interp.py` (via the already size-generic
  `us_load/us_store`), `native/rt.c` (`hs_load64/hs_store64`) and
  `x64gen.py` (`mov rax,[rax]` / `mov [rax],rcx` with no tag) - all 3 backends
  agree; tests `tests/t_load64.hs` + `tests/x64/load64.hs`
- `hs fmt` preserves hex literals (`0x83` does not become `131`) because page-table
  flags must stay readable - the parser keeps the literal's `raw`, the printer uses it
- Tests: interp 36 · native 37 · x64 26 (both files newly added)

### 15.9 bitwise operators (v0.6.1)

An OS must twiddle bits (bitmaps, page flags); the language could not at all. This added
`& | ^ << >>` and unary `~`

- All 3 backends + one shared error set: `operator 'OP' needs Ints, got A and B`,
  `shift count N out of range (0..63)`, `cannot bitwise-not T` (Bool is not an Int)

- Precedence: `or` < `and` < comparison < `+ -` < `* / %` < bitwise - bitwise binds
  tighter than `+ -` (matching C) and the parser has a separate `parse_bits` layer
- x64: `shl/sar` by cl, results cut to 62-bit signed (bit 61 is the sign bit)
  so there is a recorded divergence: `1 << 61` is negative on x64 but positive on interp
- `hs fmt` learned the precedence and spacing for `& | ^ << >>` and keeps parens when
  needed (`a & (b | c)`) - the old rule flattened only right-side `+`/`*`
- Tests: `tests/t_bits.hs` (interp+native), `tests/x64/bits.hs` (x64)
### 15.10 Real memory management on bare metal (v0.6.2)

Dynamic paging + a real frame allocator, written in pure `.hs`, really booting on QEMU

- `kernel/kmb.hs` - reads the bootloader memory map, supporting 2 ABIs (detected by
  validation): the multiboot1 spec and QEMU's own 88-byte struct (layout does not match
  the spec - QEMU uses its own `mb_buf_phys`, 20-byte entries at `0x9000`)
- `kernel/kpage.hs` - 4-level page tables (`map`/`unmap`/`translate`,
  `map_phys`/`map_user`): create missing tables, split huge pages (2MB/1GB) into
  512 children, flush the TLB (`invlpg` + a whole-TLB `tlb_flush` after a split)
- `kernel/kpmm.hs` - bitmap frame allocator over the largest usable region
  (via `std.bitmap`), reserving image/heap/bitmap, `alloc`/`free`/`free_run`
- New primitives in `x64gen.py`: `mb_magic()`, `image_end()`, `tlb_flush()`
  (plus the existing `mb_info`/`cr2`/`cr3`/`set_cr3`/`invlpg`); `mov_ri64` now takes a full
  64-bit immediate (the kernel needs every bit, e.g. `0xDEADBEEF...`)
- Bugs found on the way (all fixed): `0x83` on a 4K PTE enables the PS (huge) bit, must use
  `0x03`; `pte_addr` used the parent index to read the child table after a split; `free_run`
  called `reserve` instead of release; `unmap` returning `false` inside `unsafe:` became
  Int 0 (must return at the safe level)
- Tests: `kprim` (primitives), `kpaging` (30 asserts: map/translate/split/unmap),
  `kpmmtest` (fill the pool + return it) - xkernel 62 -> 77 cases
### 15.11 kmalloc + address spaces (v0.6.3)

OS milestone m2: a truly growable heap + a new PML4 per space - pure `.hs`, really booting

- `std/heap.hs` adds `heap_init_at(addr, nbytes)` (the old `heap_init` stays as is):
  the kernel maps frames first, then starts the free list on them
- `kernel/kheap.hs` - `init(npages)` takes contiguous frames from the PMM, `map_range`s them at
  `0x60000000`, then ordinary `malloc`/`free` (reuse from the list, coalesce on free,
  over-request returns 0 without crashing)
- `kernel/kaddr.hs` - `new()` copies every present entry of the current PML4
  (the kernel lives entirely in slot 0), `switch()` loads CR3 (flushing the TLB);
  user pages must be `>= 0x8000000000` (slot 1+) to be isolated from the old space
- x64 bug found: a global assigned raw inside one function's `unsafe:` but read in
  another function got unboxed wrongly (`raw_names` lived only per-function scope) -
  raw names now accumulate module-wide; the symptom was `x_tname` walking into garbage
  memory until `x_malloc` ran out (a fake "out of memory")
- Tests: `kheaptest` (malloc/free/reuse/patterns), `kaddrtest` (after a switch serial
  still works, mapping in the new space is invisible to the old, still there when back) -
  xkernel 77 -> 87 cases
### 15.12 Cooperative tasks in ring 0 (v0.6.4)

A yield-based scheduler (not preemptive yet): policy in `.hs`, mechanism in the encoder

- `kernel/ktask.hs` - `spawn(func)`/`run()`/`yield()`/`exit()` over a
  round-robin queue (parallel ctx+state lists); an entry is a plain Func `f()`
  (closures work - caps ride in r15); it must end with `exit()` or the corpse gets
  scheduled again (documented, not guarded)
- Mechanism in `x64gen.py`: `ctx_swap` (save/load callee-saved + rsp + rip then
  jmp to the new rip), `task_run` (records the scheduler in a slot for returning tasks),
  `task_init` (zero regs, r15 = func+16, rip = func code, plant `task_exit`
  as the return address), a `task_exit` stub (switches back via the recorded scheduler)
- Big bug found: `image_end` did not include the main stack (16KB) - the PMM handed out
  frames over the stack, breaking locals/return addresses; symptoms appeared far away as
  wild jumps (`EXC 6`), ghost errors (`index must be Int` on correct values), layout
  dependent; chased with disassembly against Python for a long time; the EXC report now
  prints fault RIP + CR2 so no more guessing
- Tests: `ktasktest` (3 tasks sharing a counter, all exit, back to main) -
  xkernel 87 -> 94 cases
### 15.13 Preemptive scheduler (v0.6.5)

Timer IRQ0 switches tasks by itself: stub + a `.hs` tick handler + switching in the stub

- `kernel/ktask.hs` - `tick()` (read-only, no print/alloc) returns the target block when
  the quantum ends, `preempt_on/off()`, `npreempted(i)` counts preemptions;
  `spawn`/`exit` bracket mutation with `irq_off/on`
- Mechanism in `x64gen.py`: the stub saves all 15 regs + rsp + rip (never touching rflags),
  calls the handler on the same stack (bounded, nest-safe), Null return = restore +
  iret, a block return = save + full-load + jump (rip always paired with rsp:
  fresh -> entry, preempted -> tick_back + iret, suspended -> resume + ret);
  `irq_off/on`, `sched_on_tick(f)`/`sched_tick_clear()`, a depth counter against
  nested ticks (skipped, slot untouched)
- Big bug found: the IDT uses interrupt gates (0x8E), so the CPU clears IF on entering
  the stub, but the jmp-style switch path never restored it - the first preempted task
  ran deaf (IF=0) until `exit()` did sti for it; the symptom was spans collapsing into a
  single tick despite full counts; chased with IF-sampling + PIC/APIC/monitor;
  adding `sti` before the jump fixed it
- Second bug: `ctx_swap_inner` saved only callee-saved - a task woken by a cooperative
  load got stale caller regs (counts silently vanished); now full save/load in both the
  inner path and the stub (using push_m + ret because no scratch register is free)
- Tests: `kpreempt` (a hog that never yields but waits on ticks until certainly switched +
  exact counts + everyone gets switched) - xkernel 94 -> 99 cases
### 15.14 filesystem: ramdisk + VFS (v0.6.6)

The OS's first filesystem - all pure `.hs`, no block driver

- New builtin `read_mem(ptr, n)` -> a Str of raw bytes (byte-preserving) on every
  backend; before, memory could only be read one byte/word at a time in `unsafe:`, which
  cannot be joined into general strings - the kernel must read bootloader structs in
  chunks (needs Strs because a KRFS `path` is bytes, not numbers)
- `kernel/kvfs.hs` - inodes as parallel lists + bytes as Strs: `mkdir`/`mkdirs`
  (split levels), `create`/`write`(replace whole file)/`read`, `ls`, `stat` ->
  `[kind, size]|null`, `is_file`/`is_dir`, `unlink` (dirs must be empty; an inode still
  open becomes dead -> stale fds), an fd layer `fopen`/`fread`/`fwrite`/`fseek`/
  `ftell`/`fclose`. No cwd - always resolves from root, `.`/`..` work
  - fd-layer names start with `f` (`fopen` not `open`) because `open/read/
    write/close/mkdir/ls` are language builtins: `.hs` must not clash with them
- `kernel/kramdisk.hs` + `scripts/mkramdisk.py` - read the multiboot module
  (`kmb.mod_start/mod_end`) as a KRFS image and unpack it into `kvfs`: every field
  pads up to 4 bytes so `load32` alone can read it (no alignment assumptions),
  paths ordered by depth -> the whole tree built in one pass
- Tests: `tests/t_vfs.hs` (66 assertions on interp + native) and
  `tests/x64/vfs.hs` (x64 must match exactly), `kernel/kfstest.hs` (real QEMU boot
  with `-initrd`: loads 4 entries then reads/writes/deletes)
### 15.15 Bugs found while building the filesystem (v0.6.6)

- A function name clashing with a builtin: `kvfs.read(fd, n)` was parsed as a call to
  the `read` builtin (wrong arity -> error) because x64 used to emit builtins first;
  fixed by letting user `def`s shadow builtins (interp/native already did),
  but names on the `XBUILTINS` list stay builtins forever, because capture
  analysis skips those names (otherwise the capture slot is never created)
- `image_end()` must include the **boot page tables**, not just the file end:
  the tables sit after the page-aligned `.data`; if `image_end` is too small the PMM
  hands out frames still in use as tables, and the freshly initialized heap writes over
  them -> PDPT[0] becomes 0 -> `#PF` (writing in the bump heap at 0x2008ca0), then the
  handler itself fetch-faults at 0x101dc1 -> double/triple fault -> reboot loop until
  QEMU times out (a Heisenbug-like symptom: moving code slightly made it vanish, because
  the layout changed what happened to overlap) - fixed as `max(stack_top, end of tables)`
  + moving the main stack into `.data` so it never collides with bootloader data QEMU
  places after the image, plus reviving `busy()` + assertions in `kpmmtest` as a guard
- The runtime's bump window (`alloc()` -> Str/List/page tables/bitmap at
  `0x2000000`, 16MB) sits inside the PMM's pool too and must be reserved out

  Otherwise kmalloc and the bump allocator silently overwrite each other
  (each believes it owns the same frame)
### 15.16 user mode + syscall (v0.6.7)

Real ring 3: the kernel loads a static ELF (ordinary `xbuild`, passed as a multiboot
module), runs it, and serves syscalls with a `.hs` handler, then returns to the kernel -
all pure `.hs` (encoder mechanism), no C

- `kernel/kuser.hs` - ELF loader: walks program headers, `map`s every `PT_LOAD`
  at `vaddr + USER_BIAS` (PML4 slot 1+; the kernel side is supervisor-only),
  maps writable first then `protect`s text back to read-only (W^X), an 8-page
  stack; `run()` = `enter_user(entry, frame)`
- `kernel/ksyscall.hs` - `dispatch(nr, a1..a6)`: write (fd 1/2 -> serial),
  mmap (anonymous, kernel-chosen address), exit (records the code + `user_stop()`);
  the exit code is opaque (already tagged, used as is, Null -> 0)
- stub in `x64gen.py`: park/tag/handler/untag as before, but the stack is its
  own 16KB syscall stack (user rsp is not trusted) and the way back is `sysret`
  (restoring rcx/r11/rsp from slots); `user_stop()` returns through `user_cont_` on
  the same stack; `enter_user` ends with `sti` (this path arrives with IF=0 but the
  kernel runs IF=1)
- Tests: `kring3` (exit), `kring3ret` (sysret back, then an hlt fault with USER
  rip + CS=0x23), `kring3wr` (write to serial then exit),
  `kusermode` (a real ELF prints fully, exit 0, back to the kernel) -
  xkernel 105 -> 126 cases; `tests/x64/asptr.hs` guards the `as_ptr`/`as_int`
  below - 322 cases total, all passing
### 15.17 Bugs found while building user mode (v0.6.7)

- `syscall` is not an interrupt: the CPU saves only rip->rcx and rflags->r11, pushes
  no frame, does not switch stacks - the first stub version behaved like an IRQ (parked
  under a 40-byte "frame" that does not exist + returned with `iretq`) so it popped
  garbage: parked over its own user stack, `iretq` read garbage RIP/CS (`EXC 13` or
  `#PF` depending on the garbage); during debugging we suspected the EXC reporter read
  the RIP from the wrong slot (counted 136 instead of 128) but disassembly proved 128
  was right all along - lessons: verify with objdump before blaming the reporter, and
  never read serial output while QEMU is being terminated (you see half and misread it);
  in short: `syscall` enters (rcx/r11, stack untouched), returns via `sysret`
  (no frame to pop); only IRQs/faults use the TSS + iretq
- `as_ptr(x)`/`as_int(x)` on already-unboxed variables: `sev()` converts a dynamic slot
  to a raw word, then `as_*` checked the tag + shifted again - pointers whose low bits
  are not 00 got rejected/mis-shifted; fixed by making `is_raw_expr` return True for a
  `var` (one read is enough) + test `tests/x64/asptr.hs`
- `pte_addr` always created mid-level tables as supervisor: a user page got a user leaf
  but a supervisor path, so it faulted at the first `iretq` - the U/S bit must ride down
  the whole path (old tables upgraded on first encounter)
- GDT user descriptors were wrong: `| 3` only set limit bits, not DPL - DPL stayed 0 and
  `iretq` to ring 3 `#GP`ed; the access byte must really be 0xF2/0xFA (DPL=3)
- `EFER` was written with `or eax, 0x100` which sets only LME (bit 8), not SCE (bit 0) -
  `syscall` was `#UD` even though the MSR was "written"; it needs `0x101`
- `IA32_LSTAR` is `0xC0000082` not `0xC0000080` (that is EFER - overwriting it breaks
  paging), and `EDX` must be cleared before `wrmsr` (MSRs are 64-bit)
- `sysret` without REX.W is compat-mode (CS = STAR base becomes a data selector
  `0x13`, fetch dies instantly); `48 0F 07` is needed to get CS=0x20/SS=0x18
- The sysret half of `STAR` must be base `0x10` (giving CS=0x20/SS=0x18), not
  `0x18`; added `FMASK=0x200` (mask IF on entry) for a future with IF=1
- The hand-written stub had `48 B8` (movabs **rax**) where `48 BE`
  (movabs rsi) was meant - overwriting its own syscall number with an address, giving a
  silent ENOSYS; the guard is asserting every byte like `kring3` does (this case teaches
  asserting from the very first `mov eax,1`, not just the later parts)
### 15.18 shell in ring 3 + file syscalls (v0.6.8)

User code reaches the VFS through the same syscall numbers as Linux - paths are `(ptr, len)`
because hs Strs have no NUL:

| nr | syscall | what it does |
| --- | --- | --- |
| 0 | `read(fd, buf, len)` | fd 0 = keyboard (one line), others = file |
| 1 | `write(fd, buf, len)` | fd 1/2 = serial, fd 3+ = file write |
| 2 | `open(path, len, flags)` | 0 = read, anything else = write -> user fd = kvfs + 3 |
| 3 | `close(fd)` | |
| 59 | `exec(path, len)` | load an ELF from the VFS over the current image |
| 78 | `ls` / 83 `mkdir` / 87 `unlink` | straight through `kvfs` |

- `kernel/ksyscall.hs`: `copy_out(dst, s, n)` copies a Str into user memory,
  `readline()` spins on `readkey()` after `irq_on()` (the syscall path arrives with IF=0
  so keyboard IRQs never arrive), backspace = byte 8 built once from `alloc`
  (hs escapes have no `\0..\8`)
- `exec` uses `exec_enter` (an iretq that does not save a continuation), separate from
  `run()` - `run()` would overwrite the old session's continuation/stack
- `scall(nr, a1..a6)` = a new builtin of x64 hosted (emits a raw `syscall`,
  returns an Int) letting `kernel/uush.hs` = a ring-3 shell (`help echo cat ls
  mkdir rm write run exit`) also be written in pure hs
- Tests: `kiotest` (calls the file syscalls from ring 0 directly - deterministic, no
  key typing), `kushtest` + two real shell sessions on QEMU
  (`caa\x08t /motd` fixing a word with backspace, `write`+`rm`, `run /nope` then
  `run /bin/hi`) + `tests/x64/scall.hs` - x64 31 -> 32 suites,
  xkernel +145 assertions (274 total)

### 15.19 Bugs found while building the shell (v0.6.8)

- `copy_out(buf, s)` called Str `len()` but the arity was never checked (a gap
  in the x64 subset) -> the unbound `n` became a Func -> `cannot compare Int and
  Func` - caught immediately by `kiotest` because no timing guesses are needed
- Resuming from ring 3 must restore the **rbp** of the frame where `enter_user` was
  called: back then the stub worked on the syscall stack and rbp was left as the
  handler's (or ring 3's), so the epilogue `mov rsp,rbp; pop rbp; ret` flew off
  and triple-faulted = a silent reboot (seen as "rebooting" on serial) - fixed by saving
  `user_saved_rbp_` on entry and restoring it before jumping to the continuation
- QEMU's `sendkey` silently drops keys when typed too fast (PS/2 overrun drops keys),
  making sessions nondeterministic - every key must be reply-checked, 0.6s/key slow,
  and typing must not start before the shell is up (the first screen is 15s)
### 15.20 Closing syscall holes + docs debt (v0.6.9)

- `user_range_ok(addr, n)` in `ksyscall`: a pointer from ring 3 must be `>=
  USER_BIAS` or it gets `-EFAULT` (14) with no memory touched - before, `read_mem`
  /`copy_out` would read/write any address (info leak + kernel corruption from
  ring 3); `kiotest` therefore pokes the path/buffer into a real user page instead
- `copy_out`/`sys_read` fd 0 guard `n <= 0` by returning 0 first (before, a negative
  `n` leaked out as a negative return, and fd 0 would enter `readline()` and hang)
- Recorded as a limitation: `write` on fd 1/2 goes through `print` so it always appends
  `\n` (byte-exact needs a new serial-write builtin - not done yet)
- Error messages went back to literals: `enter/exec_enter wants ...` split into two
  lines, `unknown variable` uses string concat (no new template) -
  `docs/errors.md` has real names again instead of `{name}/{ar['name']}`
### 15.21 Arity check in x64 (v0.6.10)

x64 never checked argument counts: a wrong call let the callee read stack garbage and
produce confused errors (`cannot add Int and Func`) - interp/native caught this from
the start (`f wants 2 args, got 1`). Following native, which stores `name+arity` in the
Func object:

- A Func is `[kind][code][nparams][name][caps...]` (caps move +16 -> +32
  in all 4 places: call sites, task_init, tick stub, syscall stub)

- Every user call compares `nparams` against the actual arg count; on mismatch the
  cold helper `arity_fail` builds `"NAME wants N args, got M"` from the struct (not a
  static name) then `hs_raise_msg` - `f = g; f(1,2)` reports `g`, matching interp,
  and try can catch it
- `task_init`/`sched_on_tick` check 0 args, `syscall_register` checks 7 args
  at registration time (the hot stub never re-checks)
- Tests: `tests/arity` (interp+native), `tests/x64/arity`,
  `tests/x64/arity_reassign` - every kernel still boots as before
  (kiotest + shell session `fails 0`)
### 15.22 hosted grows up: argv/input/env on x64 (v0.6.11)

`xbuild` programs can now read the outside world (before: only compute + print):

- `_start` stores argc/argv into slots before aligning the stack (at entry: `[rsp]=argc`)
- `argv()` = a List of `argv[1:]` (skipping the program name like interp),
  `input()` = one line (byte-at-a-time because there is no pushback,
  bare EOF = `input: EOF`), `env(name)` = scans envp for `NAME=` (missing =
  null) - all through raw syscalls on a tempered stack, no libc
- `test_x64.py` now understands `.args`/`.stdin` and passes `.env` at run time
  (the overlay used to apply only at build) - tests: `argv`, `input`, `input_eof`,
  `env` (x64 34 -> 38 suites)
- Remaining: `open/read/write/close` (needs a heap kind `K_FILE`),
  `system` (needs processes), Float/Dict/extern/attrs on values
### 15.23 hosted file I/O: open/read/write/close on x64 (v0.6.12)

- New heap kind `K_FILE` (`[kind][fd][flags][path]`) + `print`/`str`
  display `<file PATH>` + `tname` knows `File`
- `open(path, "r"/"w")` via `openat` (w = O_WRONLY|O_CREAT|O_TRUNC),
  `read` reads the whole file with growth, `write` loops until done (returns the
  byte count), `close` is a no-op when already closed - errors are `errno N`
  (unlike interp which shows strerror; recorded)
- Tests: `file` (write/read/show/compare), `file_err` (ENOENT),
  `file_errmode` (mode), `file_closed` - a 100KB file passes
  (x64 38 -> 42 suites)
- Remaining: `system`, Float/Dict/extern/attrs on values
### 15.24 system() on x64 (v0.6.13)

- `system(cmd)` via fork + execve(`/bin/sh -c cmd`) + wait4 alone
  (env inherited, failed exec = 127, killed by signal = negative like Python)
- Tests: `system` (exit 3/0 + kill -9 -> -9) - x64 42 -> 43 suites
- Truly remaining: Float (needs a representation change), extern, attrs on values
### 15.25 Module aliases on x64 (v0.6.14)

- `m = mod` / `m = pkg.sub` bind a name with no code emitted at all; `m.attr` calls
  work exactly as before (including the `has no attribute` error and `print m`)
- Nearest-wins rule: a value slot in a nearer scope wins (param/def/capture
  may shadow an import as before); a tie within one scope goes to the binding
  (because x64 scopes are flow-insensitive); assigning an ordinary value over an alias
  works (`m = 42` after `m = mod` becomes a normal value)
- Passing a module into a call/operator/index is still an error as before
  (`err_mod_value` changed to `print x + 1`; added `modalias`)
  - x64 43 -> 44 suites
- Truly remaining: Float/Dict/extern/attrs on values
### 15.26 _start reading argc broke on the kernel's stack (v0.6.15)

- v0.6.11 added the `_start` capture (reading argc from `[rsp]`) - right on Linux,
  but programs the kernel loads have no argc on the stack: they read an unmapped word
  immediately -> `EXC 14` at the very first user instruction (`kusermode`/`kushtest`
  all broke even though kiotest passed - kiotest never enters ring 3)
- A matrix proved it: old kernel + new user broken, new kernel + new user broken,
  old kernel + old user fine -> the fault was on the user ELF side (hosted emission)
- Fixed in `build_frame`: plant argc=0 and argv[0]=NULL on top of the user stack,
  then start rsp 16 lower (the frame shifted down to avoid overlap) - `argv()` is
  empty, `env()` correctly sees NULL as null
- Harness lesson: bigger binary + slow TCG meant a 10s wait showed serial cut off
  mid-way and looked like a hang - it needs 25s; raised the `kusermode` timeout 15 -> 25

### 15.27 Dict in x64 (v0.6.15)

Closing the subset's last hole: Dict, which used to be a compile error

- New heap kind `K_DICT` = `[kind][len][cap][buf]` where buf stores
  (key, value) pairs interleaved - one pair is 16 bytes, so it walks by word index
  (even numbers) and `for k in d` steps by 2
- Key lookup is a linear scan (`x_str_cmp`) - dicts in this language are small, and
  insertion order is what interp (a Python dict) already shows; rewriting an existing
  key overwrites in place (Python semantics)
- `x_dict_new` prepares a compile-time-known pair count, then `x_dict_set`
  grows 2x at a time (copying with copy_bytes)
- A literal `{"k": v}` is assembled on the stack: push every pair in source order, then
  read back at constant offsets (`16*(n-i)`) because LIFO pops would walk backwards
  - recorded as a gotcha in the code
- `x_dict_get` raises `key 'k' not found`, `d[1]` raises `dict key must be Str`
  (key type checked before index type, following interp's order)
- `x_dict_eq` returns 0 when equal (like `x_list_eq` - `x_eq` converts with
  `sete`; swapping them would silently flip `==`)
- Tests `dict` (17 cases incl. nested/equality/order), `dict_missing`,
  `dict_keytype` - x64 44 -> 47 suites; the kernel boots as before
  (kiotest `fails 0`)

### 15.28 Builtins as values in x64 (v0.6.15)

`f = str; f(65)` used to be a compile error because x64 had no trampoline

- Reading a builtin name in value position -> builds a Func object
  `[kind][code=bi_call][nparams=-1][name][caps[0]=id]` stored in a per-name data slot
  (cached), so self-equality matches interp
- The sentinel `nparams = -1` tells the call site to skip the arity check and pass
  `argc` (rdi) + the caller's line number (rsi) to `bi_call`
- `bi_call` switches on the id, compares argc, then **tail jumps** to the stub for
  (builtin, argc) emitted at the end of the code: the stub builds no new frame because
  `bi_call`'s frame already holds the arguments at `[rbp+24]` - the stub
  reads the arguments in place and closes bi_call's frame (`mov rsp,rbp; pop
  rbp; ret`), letting the existing inline emitter be reused untouched
- Wrong argc -> the message follows interp (`str wants 1 arg, got 2`) with the
  caller's line number
- `print`/`str` of a builtin is `<builtin NAME>`; `tname` is `Builtin`
  (user-declared Funcs stay a type error as before)
- Stubs are emitted only for builtins the program actually references -> programs that
  use none pay no code cost; tests `builtin_value` (through a variable/through a `def`
  argument), `builtin_value_arity` - x64 47 -> 49

### 15.29 File helpers in x64 (v0.6.15)

`read_text/write_text/append_text/exists/ls/mkdir` used to be compile errors on
x64 - file-using tools/scripts now run on this backend

- All build on the existing File runtime (openat/read/write/close)
  plus three more raw syscalls: `access` (21) for `exists`, `mkdir` (83)
  for `mkdir`, `getdents64` (217) for `ls`

- `open` gained a third mode = append (`O_WRONLY|O_CREAT|O_APPEND`) to support
  `append_text`
- `mkdir` does makedirs like interp: walk the path for `/` and mkdir each
  prefix (EEXIST skipped), then mkdir the full path - you must pass the
  Str **payload** to `x_str_at`, not the object (a gotcha)
- `ls` reads `linux_dirent64` and **scans for the NUL** to find the name length
  (never use `d_reclen - 19`: `d_reclen` is padded up to 8 bytes), skips `.`/`..`,
  then insertion-sorts with `x_str_cmp` - comparable to `sorted(os.listdir())`
- File helper error messages report `errno N` instead of interp's strerror
  (the single recorded divergence in AGENTS.md / docs)
- Test `fs_helpers` (nested makedirs, append, real/fake exists, two-level
  ls) - x64 49 -> 50

### 15.30 Raw port I/O in the kernel (v0.6.16)

`ioport_in(port, size)` / `ioport_out(port, value, size)` - a key stepping stone
to a real driver (ATA), because `asm()` exists only on the native side

- The language has no `asm` in `xkernel`, so it needed an outlet: raw port I/O lives in
  the freestanding runtime after `x_dict_helpers` as `x_port_in` /
  `x_port_out` (size = 1/2/4 bytes; `in ax,dx` 16-bit zero-extends itself)
- The builtins unbox arguments into machine words first (`sar 2`) - the port
  number and value are raw numbers, untagged
- A hosted build rejects them with `builtin 'ioport_in' not in x64 subset` like
  other kernel-only syscalls
- The assembler gained `in_ax_dx`/`in_eax_dx`/`out_dx_ax`/`out_dx_eax`
- Tested in kiotest: CMOS shadow RAM (0x70 index / 0x71 data) round-trips both
  0x5A and 0xA5, and 16/32-bit widths read 0 from an empty port -
  meaning a driver can talk to real registers

### 15.31 The OS's first ATA driver (PIO) (v0.6.17)

`kernel/kata.hs` - the first real disk read/write driver, written in pure
`.hs`, talking to the controller through `ioport_in/out` from 15.30

- primary channel / master / LBA28: IDENTIFY (0xEC), READ (0x20),
  WRITE (0x30); PIO word by word through port 0x1F0 (no DMA/IRQ needed)
- `present()` checks IDENTIFY, `read_identify()` pulls 256 words;
  `sectors()` reads words 60-61, `model()` decodes the model name (byte-swapped
  within each word, NULs mixed in - compacted first, then `read_mem` into a Str)
- `read`/`write(lba, count, buf)` validate count 1..256, `select(lba>>24)`
  + `lba_setup` before issuing the command, then `wait_ready()` checks DRDY/ERR
- Gotcha found: values read inside `unsafe:` are block-local - pass them out via
  `return` through helpers (`rd8`/`byte_at`/`put_byte`) instead of direct assignment
- The `katatest` test boots QEMU with a 1MB raw disk: identify, sector 4 matches
  its pattern, sector 9 written and read back identical, sector 10 unharmed
  - added to test_xkernel (274 -> 279)

### 15.32 Float in x64: IEEE-754 f64 without libc (v0.6.18)

The x64 subset's main gap is closed - full `Float` on both hosted
(`xbuild`) and freestanding (`xkernel`), in pure `.hs`+machine code

**Representation.** The tag bits are exhausted (Int `01`, Bool `10`, Null `11`, heap `00`),
so Float is a full heap object: kind `K_FLOAT = 5` storing raw f64 bits
(`[kind][f64]`) - no alternative that avoids changing the whole runtime

**Arithmetic.** `- * /` use SSE2 (`subsd`/`mulsd`/`divsd`); `%` uses the x87
`fprem` + sign fix to become `math.fmod` like Python (`7.5 % 2.0 == 1.5`,
`-1.5 % 2.0 == 0.5`, `1.5 % -2.0 == -0.5`); `/` and `%` by 0.0 give a
(catchable) `division by zero` like interp. An Int beside a Float converts via
`cvtsi2sd`; a Bool/Null beside a Float is an error (`cannot add Float and Bool`)

**Comparisons.** `ucomisd` - `0.0 == -0.0` is true, `nan == nan` is false, NaN is never
`<`/`>` (false for `<=`/`>=` too, IEEE style). `1.0 == true` is true because
Python treats Bool as the numbers 0/1 in `==` but *not* in `<` (interp does that)

**`print`/`str`: shortest round-trip without libc.** Python uses dtoa
mode 0 = *the shortest decimal within the round-trip interval*, not "round to
p digits and take the shortest" - a real difference, e.g.
`6.290184345309701e-235` (not `...7005`). Steps:

1. decompose to `m x 2^e`, then expand the decimal **exactly** on a 96-word
   bigint (`m x 5^-e` when `e < 0`) into a digit string
2. compute the round-trip interval once: the midpoint with the neighbor
   patterns (`P-1`, `P+1`) is `S x 2^(emin-1)`, with a flag for whether the endpoint is
   inclusive (half-even looks at the pattern's low bit) - `Lp == 0` and `Up == inf`
   have special paths
3. try `p = 1..17`: take `T` = the first `p` digits, then test `T` and
   `T+1` for interval membership; if both fit, pick the nearer one (comparing
   `(2T+1)x10^K` against `2v` on the bigint) - ties go to an even last digit
4. print Python-style: fixed when `-4 <= E10 <= 15`, else scientific;
   keep the `.0` so a float looks like a float; `inf`/`nan`/`-0.0` are special words

**`float(str)`: always parses correctly.** Keep 100 significant digits + a sticky bit
(`K` tied to the number of decimal places), then compare by cross-multiplication on the
bigint (`dec_cmp`: `L/R == D_dec/D_dbl` exactly), then binary-search the IEEE
pattern space 63 rounds, ending with a round-half-to-even midpoint decision
(comparing `2T+1` against `S x 2^emin`) - with the sticky bit, inputs longer
than 100 digits still parse correctly. No FPU reliance (avoiding subnormal/ties bugs)

**Tooling.** The assembler gained SSE2/x87 (`cvtsi2sd`, `cvttsd2si`, `ucomisd`,
`addsd`..`divsd`, `movsd_*`, `fprem`, `fnstsw_ax`, `sahf`, `fstp_st1`, `shr_cl`)
+ `adc_*`/`mul_r`/`or_ri32`/`xor_ri32` and a 7-piece bigint core
(`bi_zero`/`bi_from_u64`/`bi_copy`/`bi_mul_small`/`bi_add_small`/
`bi_shl`/`bi_cmp`/`bi_divmod_small`) - all alias-safe (read before writing each
word), because both directions are called in place

**Gotchas found along the way.**
- Values in `unsafe:` are block-local as before; new: a `return` in the
  generator makes a following `a.label(...)` dead code ->
  `undefined label`; you must `jmp` to an end label instead of a plain `return`
- A `[rbp-N]` slot reused by two variables = values silently vanish (hit 4 times:
  pointer vs loop counter, `limit` vs digit, `ecnt` overwritten by PUTAL,
  `E10c` pushed by carry) - look carefully before trusting values in gdb
- A stack buffer must be `bi_zero`ed before use, always, or results depend on
  whether the stack page was ever touched (seen as parses failing only on subnormals)
- `x_dbl_parts` returns `e = raw - 1075` (not `-1023`) because the mantissa
  already has the implicit leading 1
- The midpoint is `S x 2^(emin-1)` not `x 2^emin` (S is the sum) - forgetting
  the `-1` made every candidate one factor too small
- No libc means no `snprintf("%.17g")` - if `extern:` ever lands in x64,
  adding Float will be much cheaper than this

**Test results.** Fuzzed against `interp.py` (which is CPython) over 2500+ values
(random decimals in many forms, random bit patterns, every 2^k/10^k step,
neighbors of subnormal/zero/max-double) - all match, including `1e-08`,
`5e-324`, `1.7976931348623157e+308`; `int()`/`float()`/`str()` and error messages
match every case. Tests `tests/x64/float.hs` (x64 50 -> 51) and
`kernel/kfloattest.hs` really booting QEMU (xkernel 279 -> 284)

### 15.33 JSON in x64: compiling the parser from `.hs` source into the image (v0.6.19)

Full `json_parse`/`json_str` on both `xbuild` and `xkernel`
(`json_load`/`json_save` hosted only, since they need a filesystem)

**Chosen approach.** No hand-written JSON in machine code - instead real hs in
`runtime/json.hs` (about 430 lines), and x64gen **compiles that file into the
image** as a private module named `<json>` only for programs calling `json_*` -
detected by an AST walk before `finalize`, then `collect`ed and emitted

label `hsJF_*` and run `emit_mod_init` just like an `import`

- The one hook this module gets is `type_name(x)`, compiled straight to the
  runtime's `x_tname` (hs has no type introspection); the hook sits behind a
  `mod["name"] == "<json>"` check, so if a user writes `import runtime.json`
  themselves (possible when the repo is on HSPATH) they get another copy without
  the hook - functions needing `type_name` will not compile (`unknown variable
  'type_name'`); helpers that need no introspection still work
- The entry point returns a 2-element List: `[null, value]` or
  `["<message>", null]`, and the wrapper emitted in `ev_call` does the
  `hs_raise_msg` with the **caller's line**, so the error text matches
  CPython (which interp uses) exactly: `Expecting value`, `Extra data`,
  `Expecting ',' delimiter`, `Illegal trailing comma before end of array`,
  `Unterminated string starting at`, ... plus
  `json_str failed: Out of range float values are not JSON compliant: inf`
  and `not JSON-serializable: Builtin`
- The parser/encoder is byte-oriented (an x64 Str is a UTF-8 buffer), so it
  reads byte values as Ints - done with `byte_at()` = `as_ptr` + `load8`

**Things found along the way (important).**
- **`and`/`or` on x64 do not short-circuit** - both interp and native
  short-circuit but x64 ran both sides -> `while i < len(s) and s[i] == "x"`
  breaks instantly (`index out of range`); fixed by writing bound checks as
  separate calls (`js_at(s, i, n)` returning -1 past the end) and comparing
- **hs has no `chr()`** but the encoder must mint raw bytes (the UTF-8 parts
  that cannot be escaped); the only subset route is `alloc` + `store8` + `read_mem`
  (`js_chr`) - much slower but correct
- **`append()` returns Null** (like interp), not the list -> you must mutate the
  list in place, not `x = append(x, y)`
- **Registers cannot keep values across a `call`** - early on the error
  message lived in rcx across an `x_str_at` call building the `"json_parse failed: "`
  prefix; rcx got clobbered. Moved to the stack
- **x64 has no mutual recursion** and resolves module-level names statically
  -> array/object parsing had to merge into one self-calling `js_value`
  (computed in `runtime/json.hs`; with no `int()`/`ord()` available to tell
  Int from Float, it uses `str()` + first char or `len()` + first char instead)
- **an x64 list is `[kind][len][cap][buf]`** - elements live in buf, not
  inline -> the wrapper reads `[[rax+24]+8]`, not `[rax+16]`
- `finalize()` used to bound capture hunting at the `<main>` module scope, so
  module-level names of other modules looked like captures (then reading an
  unassigned global = `unknown variable`); fixed to stop at its own
  module scope (`p is p._mod.get("scope")`)
- A Python `return` inside the emitter makes a following `a.label(...)` dead
  code (undefined label) - json_save therefore emits the whole block inline
  instead of a `jmp` to the function's end label
- **The x64 tests gave no stack warning** - the evidence was `gdb` showing
  `mov 0x8(%rdi),%rax` with rdi = 0, traced back up the call chain

**x64 bugs found during this work (fixed).** `int(x)` on an Int passthrough
path did not `pop` the value pushed for the message
-> left 8 stale stack bytes, making `s[int(n)]` read the wrong operand
(`cannot index Int`) plus stack drift in complex expressions. This adds
regression coverage at the end of `tests/x64/float.hs`

**Check results.** Differential test against interp (i.e. CPython): 44 encode
cases + 79 decode cases - everything matches: stdout, stderr and exit codes,
including error messages and line numbers. Tests `tests/x64/json.hs` (x64 51 -> 52)
and `kernel/kjsontest.hs` really booting QEMU, 18 assertions + 4 errors
(xkernel 284 -> 291)

### 15.34 Exponent float literals + native shortest float printing (v0.6.20)

Asking "is the language 100% complete" opened two holes that were not missing
spec features but real bugs to fix

**1. `1.5e3` was not a float.** The old lexer had only
`[0-9]+\.[0-9]*|\.[0-9]+`, so it cut `1.5e3` into `1.5` and left
`e3` to die as `unknown variable 'e3'` - a Python-indented language that could not
write exponent notation. The regex is now
`[0-9]+\.[0-9]*([eE][+-]?[0-9]+)?|\.[0-9]+([eE][+-]?[0-9]+)?|[0-9]+[eE][+-]?[0-9]+`
and it keeps `raw` so `hs fmt` returns the original form (`1.5e3` does not become
`1500.0`) - `0xFF` was already kept the same way

**2. Native Float printing mismatched interp on 48% of values.** `v_disp` in
`native/rt.c` used plain `%.17g`, printing 17 significant digits for every
inexact value: `print 0.1` gave `0.10000000000000001` while interp gave `0.1`.
Fuzzing 674 values matched only 322 - **this bug existed since Float entered
native (not from this round) and was never caught because no test printed an
inexact float**. Fixed with `fmt_repr()`, which finds the shortest significant
digits (trying 1..17 and checking `strtod` reads back the same value), then
formats like CPython: fixed when 1e-4 <= |x| < 1e16, a `.0` when integral,
at least 2 exponent digits -> passes 2021 values across 3 fuzz seeds, now 100%

**3. x64 bug found during the work: `float("1e309")` gave nan.** Discovered while
fuzzing floats after fix 2 (seed 77) - `nearest_double()` binary-searched the
IEEE pattern space with `hi = inf`, stepping `lo = mid + 1` for 63 rounds; when
`lo` met `hi` exactly at inf's pattern, the next step walked past it into NaN
(`0x7FF0000000000001`) and returned nan. Fixed by clamping
`lo = min(mid + 1, hi)` -> everything beyond max double becomes `inf` per Python

**4. Native needed a way to write literal `inf`/`nan`.** `repr(float('inf'))`
gives `inf`, which is an identifier, not a C constant (gcc error), so
`hs_f64raw(uint64_t)` was added to `rt.c` and the emitter writes the bit pattern
directly (`v_float(hs_f64raw(0x7ff0000000000000ULL))`) instead of binding `math.h`

Evidence: `tests/floatlit.hs` (interp 42 / native 43), a longer `tests/x64/float.hs`,
`tests/test.py` 41 -> 42, `tests/test_native.py` 42 -> 43

### 15.35 Middle IR: a CFG every backend must eat instead of the AST (v0.6.21)

The first step of the self-hosting plan (`docs/superpowers/plans/2026-10-08-ir-backend.md`):
`ir.py` builds a flat CFG from `interp`'s AST - expression temps are pure SSA
(`%1`, `%2`, ...), source variables live in a frame (`stvar`/`load`), flow is explicit
blocks (`jmp`/`br`/`ret`), with a verifier (duplicate labels, jumps to missing
blocks, undefined temps, bad phis) and a reference interpreter that must match `interp`
byte for byte on stdout/stderr/rc

Key decision: `and`/`or` lower to branch+phi (short-circuit like
interp) - this is exactly where current x64 is wrong (it ran both sides), and the x64
backend must do real branches when it moves to IR (Task 4). Variables get no mem2reg
from the start (waiting for Task 3) so closures/forward-refs/path-dependent definedness
are correct by construction - 590 random differential fuzz programs all matched
(the remainder were fuzzer-made infinite loops, hanging identically on both sides)

An intentional, recorded divergence in `ir.py`: `break`/`continue` outside a loop and
`return` outside a function are clean `error:`s, while interp lets the exception
escape as a traceback - matching the traceback exactly is impossible because it is
bound to `interp.py`'s own file layout

Evidence: `ir.py`, `tests/test_ir.py` (16 differential + 4 verifier/builder
+ dump + unsupported), `tests/run_all.py` gained suite 9, `docs/errors.md`
has an `ir.py` section (via `scripts/gen_errors.py`, which now knows `ir.py`)

### 15.36 Containers + `for` in IR (v0.6.22)

Task 2 of the IR plan: `list`/`dict` literals, `index`/`slice`, `setindex`,
`for` (desugared to len/index/while over private frame slots `$itN`/`$iN` -
they cannot clash with user code because `$` cannot be written in source), plus
the `range`/`append` builtins (reusing the same functions as interp, so messages match

by construction)

A bug the differential test caught: `continue` in a `for` skipped the increment
step (hanging the whole loop) - fixed with a middle incr block: fall-through from
body/break/continue enters the increment block before returning to the header,
while `while` uses its header directly as before (split by `incr: None`)

Evidence: `tests/test_ir.py` 23 -> 47 (16 container/`for` cases +
`forcontinue` + a corpus differential over the whole `tests/*.hs` store: 9 pass,
33 skipped outside the subset, counted separately), plus 292 more random fuzz
programs all matching (882 cases across both rounds; the remaining timeouts are
genuine infinite loops in the source, hanging identically on both sides)

### 15.37 Dominance verifier + IR text form + `hs.py ir` (v0.6.23)

Task 3 of the IR plan: the verifier now checks def-dominates-use for real
(iterative dataflow dominators; a phi arm must dominate the source block of its
edge; unreachable blocks are exempt but still need a well-formed terminator),
plus a standard text form: `hs.py ir prog.hs` prints the CFG (`func key(params):`,
`label:`, `@line` at the end of every line, `-` for None, string escapes `\uXXXX`
including surrogate pairs) and `parse_module` reads it back - round-trip is equal
both as text and as execution, across every case in `test_ir.py` including nasty
strings (quote/backslash/NUL/Thai/astral/ending with ` @3`)

Bonus: `_jerr` in `hs.py` was called but never defined - the `--json` error path
had been broken with a NameError all along. Fixed in 6 lines to match the
`{"file","line","message"}` contract the docs promise, with a regression test
(`hs-ir --json`)

Evidence: `tests/test_ir.py` 47 -> 83 (dominance unit + 33 round-trip +
`hs.py ir` dump/--json), `docs/errors.md` grew an IR messages section

### 15.38 IR -> x64: a second backend eating IR directly (v0.6.24, Task 4 part 1)

`irx64.py` is a Gen subclass reusing x64gen's whole runtime
(value model, heap, builtins, errors) and leaf emitters
(emit_add/compares/arith/bitop/un/print/call/func-construct) - the only new code is
the driving layer: temp/name -> frame slot, IR block -> label, phi -> store on the
edge, calls through one protocol for both user functions and builtin values,
`hs_main`/`_start`/link epilogue identical to build_image

A trap found: some x64 builtins have no value form (`float`,
file helpers) - `load float` then calling through the value protocol segfaults
(garbage r15) because ev_call's numeric arms are inline emitters.
Fixed with provenance: a temp loaded from an inline-only builtin that feeds only
call-fn gets a dummy (the inline path discards the value anyway); anything else
errors `is not a value` as before; shadowing (user's `float = 5`) stays correct
because the scope chain is always resolved first

Evidence: `tests/test_irx64.py` compares ELF against ELF (IR path vs AST path)
9/9; the rest are skipped with separate counts (containers = next slice; try/import/
unsafe = later work; the ref itself rejects another 9)

### 15.39 irx64 part 2: containers + direct inline builtin calls (v0.6.25)

- Container ops complete: build_list/dict (stack + x_list_new/x_dict_new),
  index/slice/setindex (transliterated from ev_index/ev_slice/ex_setindex),
  iterseq (List/Str pass, Dict becomes a list of keys through a machine-code
  loop with no calls inside) - `for` works on the IR path
- Direct builtin calls must be inline: fuzz caught IR-path `len` of an Int
  reporting `len of Int` with no line number (the stub baked in line 0) while
  the AST path had one - because ev_call has an inline arm separate from the
  value protocol. Fixed with provenance: a temp loaded from a builtin in
  INLINE_DIRECT ({float,len,str,int,range,append}) that feeds only call-fn and
  is not shadowed calls the inline emitter (errors land on the right line);
  first-class use still goes through the stub as before
- `for k in dict`: IR takes a keys snapshot like interp, while old x64gen
  walked the live buf - the IR path is more correct here (the harness accepts
  a match against either side)

Evidence: `tests/test_irx64.py` 9 -> 13 (for/func/types/t_strfun),
ELF-vs-ELF fuzz over 240 cases all matching

### 15.40 import end-to-end on IR (v0.6.26, Task 4 part 3)

- `ir.py`: the builder accepts `import`/`attr`/`setattr`; the interpreter has a
  real module registry (interp-style file resolve, dotted + shell package,
  circular error, `in module` wrap, init runs once, attr read/write,
  `print mod` shows `<module name>`) - `tests/t_import.hs` matches interp
  byte for byte
- `irx64.py`: resolves at build time (parent-first + shell + circular),
  merges funcs with a dotted prefix, per-module globals, hsM_init-style
  init guard, static attr resolve (a submodule is a phantom temp whose
  value-use errors clearly), exact `print mod`; module copies
  (`x = mod`) are a recorded hole
- Traps: an alias-load must skip emission when every use is a chain
  (otherwise the UNBOUND check fires before the attr resolves); nested attr
  (`std.str.trim`) must accept an mval, not only a mod

Evidence: `test_ir.py` 83 -> 86, `test_irx64.py` 13 -> 18
(t_import/t_pkg/t_std pass; t_heap still fails on unsafe, correctly)

### 15.41 try/except/finally/raise on IR at both layers (v0.6.27, Task 4 part 4)

- `ir.py`: new ops `try_push/try_pop/exc_str/exc_pop/unbind/reraise`
  and a `raise` terminator; the builder inlines finally on every abrupt exit
  (return/break/continue with the x64gen depth rule via trystack),
  full handler shapes (nested guards for errors inside handlers + finally,
  save/restore per the whole-function shadow analysis); the interpreter uses
  Python exceptions + a per-frame handler stack (_Jump crossing _call)
- `irx64.py`: transliterated straight from ex_try (hs_try_push0/pop,
  hs_exc_str/pop, hs_reraise, hs_raise_raw/Msg) with the exc runtime +
  data emitted when a try exists; bare raise is checked at build like x64gen
- Fuzz caught more: `len` losing its line (already fixed via inline last round),
  and this round a `try_push` paired with a module-level `unbind` that was
  forgotten (no slot, because entry-stvar is a global)

Evidence: `test_ir.py` 86 -> 108 (10 try cases + corpus t_try/t_finally/
t_closure/t_circ pass), `test_irx64.py` 18 -> 22, try fuzz over 350 cases
plus x64-diff over 370 cases all matching

### 15.42 `unsafe:` on IR at both layers + xbuild switches to IR (v0.6.28, Task 4 part 5 + switchover)

- `ir.py`: the static world becomes real ops, not hidden Python variables
  - constants/variable fetch/operators: `sconst`, `sload`, `sraw`, `snz`,
    `sbin`, `sun`, `sfield`, `sderef`, `ssizeof`, `scall`
  - print/read-write/bind: `sdecl`, `sset`, `sstore`, `sfstore`, `box`,
    `svarptr` (as_ptr/as_int of a variable directly - x64gen does not unbox
    first; the tag dispatches, same code as x64gen)
  - shape-bound errors (`str`/`float` literal, collections, attr, slice,

    result) move to a runtime `serr` carrying both sides' messages (`imsg`
    for interp / `xmsg` for x64) so stdout matches even on errors, whose
    positions differ (build time for x64gen vs runtime for interp)
  - interpreter: `UnsafeVal` follows `interp.sev*` exactly - I64/U64/Ptr/LIT
    cannot mix, a pointer cannot be `Ptr`-ed, `U64` too large to box as Int
    fails; simulated 1MB memory (`_us_alloc/_us_load/_us_store`) + `read_mem`
    bound to that image
  - a variable that was `sdecl`-ed and is then read from safe code must be
    coerced back (`dset`), not overwritten with a dynamic value directly
- `irx64.py`: lowers per x64gen's `sev*`/`ex_unsafe` word for word
  (raw words with no tag check, truncating `/`, `print` uses `print_int`,
  `fstore` pushes the address before loading the value, `as_ptr` dispatches
  on tag), a struct-typed pointer comes from a `Ptr:X` declaration + `+`/`-`
  propagation + nested field (`_struct_of`), a duplicate name in one scope
  fails at build, `serr`/`ssizeof` use the x64-side messages
- JSON on IR: `runtime/json.hs` compiles as a normal module (`<json>`), then
  `json_*` calls through the same `call_js_entry` + `js_finish` set; the only
  hook is `type_name` in that module (matching the old AST path)
- **Switchover**: `x64gen.build_x64` now walks parse -> IR -> verify -> GenIR;
  the old path moved to `build_x64_ast` as the reference for `test_irx64.py`
  and remains the path `xkernel` (freestanding) uses
- Fuzz catches: nested `and`/`or` made a phi arm point at a non-predecessor
  (you must read the real target label after evaluation), `sraw` leaking into
  `sbin`, `ssizeof` leaving the struct unknown at build, module alias copies
  (`x = mod`) dying because the alias was created at emit time but dead-load
  was computed at plan time

Evidence: `test_x64.py` 52/52 pass on the IR path, `test_irx64.py` 22 -> 35
(ELF-vs-ELF against the old path; cases that differ get a `!!` flag noting the
IR path is more correct, e.g. the `tests/ufunc.hs` segfault the old path hit),
`test_ir.py` 108 -> 134, fuzz over 480 cases (IR + x64) all matching

### 15.43 `hs.py xkernel` working again + stuck QEMU cases all pass (v0.6.29)

- A real bug that escaped back in v0.6.23: while inserting the `ir` branch into
  `hs.py`'s `main()`, the line `if argv[1] == "xkernel":` vanished into the
  `xbuild` branch, making `hs.py xkernel` flow into the native backend (gcc)
  and die with TypeError - the test suite missed it because it calls
  `x64gen.build_xkernel` directly, not through the CLI
- Added 3 regression cases to `test_x64.py`: scan `hs.py`'s AST to confirm each
  subcommand has one branch and no duplicates (`run` is an intentional
  fall-through with no branch) + build a real freestanding ELF through the CLI
- The long-stuck QEMU cases (`kio` EXC 14 x3, `kush` sendkey) all pass in a
  full round: `test_xkernel.py` 291/291 - they had been a QEMU environment
  problem (passing standalone since before), unrelated to the IR work

### 15.44 Five real x64 bugs the old suite could not see (v0.6.30)

Opening `xbuild` through IR required proving the new path matches across the
whole language, not just passing `tests/x64/` - so the corpus walker now runs
all of `tests/*.hs` through the IR path and compares run results against
`interp.py` (build errors matching `.fail` count as pass, outside-subset counts
as SKIP, documented differences show as "known divergence" instead of a silent
SKIP). That surfaced bugs no test ever covered:

1. **`Int / Int` returned Int** instead of Float - breaking the language contract
   (`7 / 2 is 3.5`); old x64 fell through to `idiv` despite having a float path.
   Fixed with `cvtsi2sd` + `divsd` (half-to-even rounding, matching interp's
   `float(int)`) on the safe path of both backends; `unsafe:` keeps C-style
   truncation as previously specified
2. **`%` followed C, not Python** - `-7 % 3` gave `-1` instead of `2` (add the
   divisor when remainder and divisor have opposite signs)
3. **A nested def calling itself broke** - the closure captured before `var_set`
   bound its own name, so reads got UNBOUND; fixed by reading captures **after**
   `var_set` (AST path) and pointing the self-capture at the object being built
   (IR path)
4. **`json_load` passed a closed File to the decoder** - a slot pushed at the
   wrong offset (`add $8` before `pop`); no test covered it, since
   json_parse/json_save passed all along, so it only showed on the full corpus walk
5. **`x_str_cmp` decided by length alone** - `"ab" < "b"` was false, making `ls`
   **reverse** the listing, and breaking dict lookups where one key is a prefix
   of another; fixed to scan shared bytes first, then decide by length
   (also fixed `x_list_sort_str`, which used `rcx`, clobbered by `x_str_cmp`,
   as its swap index)

Knock-on fixes: `kernel/kmb|kpage|kpmm.hs` had long used `/` in safe code for
integer division (leaning on the old bug) - changed to `int(x / y)`; freestanding
`1 / 0` still raises `#DE` because SSE divide does not trap (added an `idiv`
guard for it); `tests/x64/fib.expected` had recorded `20 / 4` as `5` per the bug -
fixed to `5.0` per interp; `test_xkernel.py` gives session B 30 seconds (the old
20 was a cliff edge once images grew)

Evidence: `test_x64.py` 52 -> 97 (added the full corpus walk + 3 CLI cases),
`test.py` 42 -> 48, `test_native.py` 43 -> 49, `test_ir.py` 134 -> 138,
`test_irx64.py` 35 -> 41, `test_xkernel.py` 291/291

## x64 backend limits and how `hs run` picks a backend

- `hs run` tries x64 first (build ~0.1s, no gcc); if the program is outside the
  subset or has an Int literal beyond 62-bit it falls back to native (gcc) or
  interp on its own
- **Int on x64 is 62 bits wide** (-2^61 .. 2^61-1), while interp uses Python ints
  (unbounded) and native uses 64-bit. Overflowing values are **not silently
  truncated**: a hosted build traps with `error: Int outside the 62-bit range ...`
  exit 97 (add/sub/mul/shift/tag assembly). If no output/side effect has happened
  yet, `hs run` re-runs with a slower backend itself; otherwise it prints a clear
  error + hint
- Values in `unsafe:` are raw machine words with no 62-bit check; the kernel
  (freestanding) still cuts to 62-bit as before
- `true == 1` is `true` on every backend (like Python/interp)
- Force a backend: `HS_BACKEND=auto|x64|native|interp` or `hs.py run prog.hs --backend X`

### Default args (parse-time desugar)

- `def f(a, b=1 + 2):` defaults may only follow params without defaults
  (otherwise a parse error)
- Calling `f(x)` (with f a top-level `def` whose name is unique) makes the parser
  fill each missing trailing argument with a copy of the default expression
  **on every call** (unlike Python, which computes it at def time;
  `[]` gets a fresh list each call) - every backend therefore only ever sees
  full-arity calls
- Not yet supported: methods inside a class (parse error), calls through another
  variable/lambda (you get the normal arity error), `selfhost/cc.holy` (rejects)
- Tests: `tests/t_defaults.hs` (every backend), `tests/err_defaults.hs`

### Runtime allocation: strings
String length and contents are unchanged. x64 string copy/concatenation
allocates the 16-byte object header plus payload, rounded up to 16 bytes.
No extra spare block is required: strings are immutable and all readers use
the stored byte length. C-string conversion keeps its separate terminator.

### Unsafe C ABI entry invocation (Linux x86-64)
`unsafe: I64 result = call0(Ptr)` invokes a non-null address using the C ABI
with no arguments and an I64 return. The caller owns executable memory, ABI
correctness and lifetime. The interpreter permits only foreign pointers
when extern has enabled foreign memory; simulated arena pointers are
rejected. Null is a catchable error. Invalid non-null addresses can crash,
as with other unsafe memory operations. This does not call hs functions
with their internal ABI and is unavailable in freestanding kernel mode.
### Executable memory groundwork (Linux x86-64)
`selfhost/jitmem.hs` owns a page-rounded mapping for nonempty byte lists of

at most 16 MiB. `publish` validates before mapping, copies into RW (not X)
memory and changes the whole mapping to RX (not W). Failure releases the
mapping. `release` unmaps it once and clears its handle; double release is
an error. The caller must not use an address after release or while it is
being released. This internal module does not call generated code, change
`hs run`, provide first-call compilation, or constitute a JIT. It currently
uses the system C ABI for mmap/mprotect/munmap, not a libc-free runtime.

`jitmem.publish_sections(code, data, relocate)` additionally reserves adjacent
page-aligned code/data sections. A relocation callback receives both bases
before copying; its output must be a byte list of the original code length.
Only code becomes RX; data remains RW and never executable. The entire
reservation is released together, including on callback failure.
`selfhost/jitimage.hs` adapts the current hs assembler state to these bases,
checking undefined labels and signed rel32 reach before resolving. Multiple
images have independent data and lifetime. This is relocation groundwork,
not whole-program entry execution or ELF loading.

### Experimental eager in-process compiler execution
`selfhost/be/jit_run.hs SOURCE [args...]` is a Linux x86-64 experiment. Build
the driver with the native hs compiler, then it parses/normalizes source,
verifies optimized IR, emits code in hs, relocates into RX code/RW data and
invokes the generated entry in the same native process. It does not write
or exec a target ELF. The sections-only emitter finalizes code/data without packing an ELF. The driver forwards argv and reads the
initial process environment from /proc/self/environ. Explicit shared-library paths/sonames are loaded by the host libc loader and
extern GOT slots are bound before publication. Bare short library names remain
outside the native driver subset.

This is eager whole-program in-memory compilation, not compile-on-first-call
or a tiering JIT. The generated _start exits the process, so control never
returns to the compiler driver; final memory cleanup belongs to the OS.
Runtime output/errors match the reference on the differential cases;
compile-time diagnostics are still experimental, not a parity claim. The
normal hs run command and its fallback/cache behavior are unchanged.

`scripts/run-jit-native.sh SOURCE [args...]` packages the experiment with a
verified seed, an isolated temporary native driver and cleanup. It needs
no Python/gcc at runtime, but builds the driver each time. This extra build
time is excluded from any already-built-driver startup measurements.

### Formatter preservation of NUL
The canonical spelling of an embedded NUL byte is `\0`, the string escape
accepted by the parser. Formatting a string must preserve its contents and
must not rewrite NUL as an unsupported Unicode escape. The gcc-native
backend emits literal byte lengths explicitly, preserving embedded NUL.

### Mixed C ABI register arguments
Hosted x64 extern calls independently use up to six integer/pointer/string
registers and eight F64 registers under the SysV x86-64 ABI. A mixed
signature can therefore have up to fourteen register arguments. Declaration
order is preserved across the independent register banks. Arguments beyond either bank are passed in declaration order on the
16-byte-aligned caller stack. At most 32 fixed arguments are supported. This
does not add variadic calls, callbacks or struct-by-value.

An extern U64 argument rejects a negative safe Int before entering C on all
hosted backends. This is a catchable type-conversion error, not a cast to
a large unsigned value. Bool and non-Int arguments remain rejected.

### Eager in-process extern binding
The Linux x86-64 eager driver may request sections with an unresolved extern
GOT, load declared prebuilt shared libraries with dlopen and bind all symbols
before executable publication. A missing library or symbol is a compilation
failure: target code must not run. Handles remain live for the target process
lifetime. The ordinary sections API still rejects externs unless explicitly
requested. This uses the host libc dynamic loader, not a self-written loader,
and adds no callbacks, variadics, tiering or compile-on-first-call.

Each eager extern symbol binds against its declared library handle, not an
undifferentiated process-global search. Relative library paths are based on
the source directory. Duplicate C symbol names with different library owners
are rejected by the x64 backend because its GOT is keyed by symbol name. The
name fflush is reserved to libc for runtime output ordering.

### Explicitly typed C variadic calls
An extern parameter list may contain one `...` marker after at least one
fixed parameter and before at least one typed variadic parameter. Example:
`I64 printf(Str format, ..., I64 value, F64 fraction)`. The complete hs call
still has exactly the declared number of arguments. The marker changes the
C prototype and ABI classification, not hs arity or argument conversion.
I64/U64/F64/Str/Ptr are already promoted C ABI types; no automatic type
inference, narrow integers, float32 or untyped hs varargs are added. Format
strings remain the caller's responsibility, as with any unsafe C contract.

### Relocatable native directory bundle
`scripts/build-native-bundle.sh OUTPUT` creates a new Linux x86-64 directory
with the pinned compiler, an ahead-built eager driver, hs compiler sources,
runtime data and standard modules. `OUTPUT/bin/hs run SOURCE [args...]` uses
eager in-process execution; `build SOURCE OUTPUT` uses the native AOT compiler.
The directory can move and runs without the original checkout, Python or gcc.
This is not a static cross-platform distribution: Linux, shell utilities and
host libc/shared libraries for eager FFI remain dependencies. It adds neither
first-call compilation nor tiering. Existing output directories are refused.

### Software RGB drawing foundation
`std.gfx` is a pure-hs drawing module. A surface is `[width, height, pixels]`,
with row-major packed RGB24 Int pixels. `surface(w,h,color)` allocates at most
1,048,576 pixels; dimensions are positive and at most 4096. `pixel` clips writes
outside the surface; `sample` rejects out-of-range reads. `rect` fills a clipped
half-open rectangle `[x,x+w) x [y,y+h)`; nonpositive extents draw nothing.
`blit(dst,src,x,y)` copies an entire source with clipping and snapshots the
source when pixels alias, so overlapping self-blits are deterministic.
Coordinates/extents are bounded Ints in [-1048576,1048576], excluding Bool;
colors are Ints in [0,0xffffff]. Validation precedes mutation. Callers must not
modify the surface's dimensions or pixel-list structure. This is software
raster storage only: no hardware framebuffer, font, input or window system.

### Experimental Multiboot2 framebuffer kernel
The kernel's optional Multiboot2 header requests640x480x32. Legacy Multiboot1
boot remains unchanged. `kernel/kframebuffer.hs` discovers and validates a
direct RGB framebuffer, maps device pages supervisor-writable/cache-disabled,
and draws clipped pixels/rectangles. `std.fbinfo.decode` validates byte tags
before mapping: byte-aligned8-bit RGB channels,24/32bpp, bounded dimensions,
pitch and memory extent. The initial implementation supports physical buffers
in [1GiB,4GiB) only, to avoid silently remapping the initial RAM identity map.
Boot without a supported tag raises; it never guesses a hardware address.

GRUB video setup and an ISO are needed for this path; QEMU's direct `-kernel`
Multiboot1 route does not supply the tested graphics mode. The demo is a static
software-drawn panel, not a window manager, desktop, font renderer or hardware
GPU driver. Firmware/real-machine compatibility is unverified. Protocol layout:
https://raw.githubusercontent.com/rhboot/grub2/master/include/multiboot2.h

### Bounded keyboard line editing
`std.lineedit` is a pure line-state helper for early keyboard consoles.
`create(capacity)` returns `[text,submitted,capacity]`, initially empty/not
submitted; capacity is an integer1..256. `feed(state,key)` mutates that state:
null means no event; printable ASCII appends unless full; backspace removes
one character; newline marks submitted. Other single characters are ignored.
After submission further events are ignored until `reset(state)`. A key must
be null or exactly one character, and malformed key inputs fail without edits.
This is not a keyboard driver, input queue, terminal emulator or Unicode editor.
Use only states from `create`, without modifying their fields directly.

### Native string byte preservation
The gcc backend emits literal source strings as UTF-8 bytes with explicit
byte length. `print` and `str` preserve embedded NUL bytes, including inside
lists and dictionaries, rather than using C string terminators as length.
String dictionary keys keep their complete bytes for identity/copy/JSON.
This does not change the existing native byte-index/length model into Unicode
character indexing, and does not make C extern Str arguments binary-safe.

### Formatter control-byte preservation
Canonical formatting preserves the decoded contents of string literals.
Only the language's supported escapes (`\n`, `\t`, `\r`, `\0`, `\"`, `\\`)
are emitted. Other literal ASCII control bytes remain literal bytes inside
strings; the formatter must not invent Unicode escapes that the parser does
not decode. Unknown source escapes retain the existing literal-next-character
behavior. This adds no escape syntax or Unicode semantics.

### Tiny bitmap labels
`std.font` is an original fixed5x7 bitmap label font, not a Unicode font engine.
`glyph(character)` returns seven fresh5-bit rows (bit4 is the left pixel).
It contains A-Z, digits, spaces and the listed punctuation; ASCII lowercase
folds to uppercase. Other characters use the question-mark glyph. Exactly
one character is required. UTF-8 byte-vs-character behavior remains the
existing backend limit: portable label input is ASCII only.
`measure(text, scale)` returns `[width,height]` in6x8 cells, including trailing
cell spacing. Newline starts another row. Empty text measures `[0,0]`.
`draw(surface,x,y,text,color,scale)` uses the existing RGB surface contract,
transparent background and clipped foreground pixels. No wrapping, tab stops,
kerning or antialiasing. Scale is an integer1..16; labels are at most1024
characters. Invalid inputs fail before modifying pixels. Bounds/color checks
match `std.gfx`. Surface storage must remain unmodified by the caller.


### Small cc extension compatibility
The legacy small `selfhost/cc.holy` compiler tries `<module>.holy` before
`<module>.hs` in its existing source-directory-only import lookup. Its import
subset does not gain HSPATH or dotted packages. To retain self-compilation,
its native runtime supports direct `exists(path)` calls on valid strings
using Linux access(F_OK). A missing/inaccessible path returns false; invalid
types retain the small compiler's existing type-error behavior. General
filesystem/type parity beyond this prerequisite is not claimed.

### Native `.holy` import bridge
The x64 AST/IR backends and hosted native compiler resolve module stems as
`.holy` first, `.hs` second within each search directory, without changing
search-directory priority. Source syntax and explicit input filenames remain
unchanged. Tracked source filenames now use `.holy`, with legacy `.hs` import support retained.
The small legacy compiler has a separate source-directory-only bridge. The new seed must pass independent source
comparison and native fixed-point audits before merge.

### `.holy` extension transition
`.holy` is the chosen source extension; `.hs` remains a supported legacy
extension. In the reference interpreter, reference IR, GCC path and LSP,
module resolution keeps search-directory order (source directory, `HSPATH`,
working directory). Within each directory, `name.holy` wins over `name.hs`.
Dotted module names still map to directory paths; import syntax is unchanged.
`hs test` directory discovery includes `test_*.holy`, `t_*.holy` and legacy
`.hs` names. Explicit input filenames work as before. Tracked sources use `.holy`. Native x64/hosted and small-cc bridges are also
implemented; audited bootstrap is required before accepting the migration.


### Opt-in reference IR profiling
`ir.run_module(module,basedir,profile=ExecutionProfile(...))` may collect
function-entry and basic-block counts for tiered-JIT preparation. Ordinary
execution leaves collection disabled. Counts saturate at2147483647 and storage
is bounded by1..65536 sites (default1024). Excess site events increment a
saturating dropped-event count. At most eight distinct argument-type vectors
are stored per function; further kinds mark it megamorphic. Argument values
are never stored. Collector scope is restored even when execution raises.
The snapshot is a diagnostic, not persisted feedback or a compilation trigger.
No native tier, hot-code compilation, on-stack replacement or deoptimization
is added. The existing IR reference restrictions continue to apply.

### Experimental framebuffer keyboard console
`kernel/kconsole_demo.holy` combines the validated framebuffer, ASCII bitmap
labels and bounded keyboard state into a single-line input demonstration.
Submitted text is displayed, never executed. Input display folds ASCII case
according to the boot font. Synchronous redraw is now backed by the bounded
keyboard FIFO described below; input beyond capacity is still dropped. No agent runtime, terminal
emulation, command evaluation, Unicode input or desktop is added.

### Experimental module-return probe
`selfhost/be/jit_return_probe.holy SOURCE` compiles one supported hosted module
into separate RX-code/RW-data mappings and calls `hs_main` through a no-argument
native shim instead of `_start`. On normal completion the shim restores C ABI
callee-saved registers and stack, returns to the driver and releases only the
image mappings. It initializes the target's private GC stack bound and an
empty language argument list; environment strings come from Linux procfs.
It does not install the process-entry alternate stack or signal handler.
No language values, closures, exceptions or GC roots cross between runtimes.
Uncaught target errors retain process-exit behavior; externs are rejected.
Generated heap arenas remain process-owned until exit, so repeated long-lived
module loading/unloading is NOT supported. This is a one-shot return-boundary
experiment, not a production runner, a cold/hot tier or a resumable exception
ABI. Existing eager and AOT routes and their error behavior are unchanged.

### Explicit normal-return heap destruction experiment
The module-return probe's optional `--release-heap` destroys its target GC
arenas, per-arena start bitmaps and arena table after normal return, before
releasing the target code/data image. It snapshots the current audited gcrt
layout (32-byte table rows, maximum1024arenas, 16MBminimum arena, bitmap
mapping size rounded from arena_size/128) while the image is still live.
No target values can escape. This is trusted-runtime metadata, not a security
boundary against unsafe target code. Basic count/alignment/size checks happen
before any unmap; an unmap error stops the probe without retrying destruction.
`--release-heap-checkpoints` adds explicit stdin checkpoints for tests to
inspect real process mappings before and after destruction. Default one-shot
behavior is unchanged. Neither mode closes target-opened files, reclaims
arbitrary external resources, recovers uncaught errors, supports repeated
module invocation, or shares objects/roots/exceptions with the driver.

### Native installation route
`scripts/install-native.sh NEW_INSTALL_DIRECTORY` is the normal Linux x86-64
run/build installation route. It delegates to the pinned native bundle build
without Python/gcc, requires a new destination and existing parent, and never
edits PATH, shell profiles or system links. Updates use separate directories.
The installed launcher provides only `run` and `build`, with existing hosted
subset/error behavior and no interpreter fallback. Development/reference
Python tools remain separate; installation does not remove them or claim
full CLI command parity. Seed source/fixed-point audits remain CI acceptance
gates, while install/run perform their existing checksum checks.

### Kernel keyboard FIFO
The single-CPU x86 kernel buffers up to 63 translated nonzero ASCII bytes in
a 64-slot ring. IRQ1 translates PS/2 set1 input using the unchanged map and
appends in order; unknown/break scancodes are still ignored. When full, drop
the newest byte, preserve queued bytes, and increment internal `keydrops_`
(unsigned qword, wraps modulo 2^64). No public overflow builtin is added.
`readkey()` returns the oldest one-character Str or null when empty. It
atomically removes a byte before allocating a Str, preserving the caller's
interrupt-enable state (IF), including empty reads. The producer runs under
the IRQ gate with interrupts masked; dequeue saves flags, masks interrupts,
updates head, then restores flags. No unconditional sti is allowed.
This is single-CPU only, not an SMP queue, Unicode/event system, key-repeat
policy or lossless hardware input promise. The queue can overflow while
redraw or other synchronous work delays reads. Device/hardware overruns
before IRQ1 receives a byte remain outside this software FIFO's control.

### Isolated native error-outcome probe
`selfhost/be/jit_status_probe.holy SOURCE [--heap-checkpoints]` adds a root
handler around a returning native module, yielding status0 or captured
language-error status1. It preserves target source lines and inner unwind;
a private uncalled IR try helper ensures the existing exception runtime is
emitted without altering compiler or seed semantics. The root consumes one
handler slot. Fatal exits, overflow, OOM, signals and unsafe faults remain
outside capture. On status1 raw error bytes/line are copied into driver-owned
memory before target heap/image teardown; no target object escapes. Copied
JSON outcome is printed after teardown, and captured status1 does not become
the diagnostic process exit code. Externs remain rejected. This is one-shot
isolated module execution, not shared values/exceptions/GC roots, repeated
calls, resource cleanup, individual-function ABI or tiering. The original
return probe retains its output and uncaught-error behavior. See
`docs/jit-status-probe.md` for markers and diagnostic checkpoint semantics.

### Sequential fresh native runtimes
`selfhost/be/jit_sequence_probe.holy [--checkpoints] SOURCE...` accepts1..32
sources, compiling and invoking each in a fresh independent runtime within
one live driver. Each controlled return copies any captured error then
releases target-owned heap/image before the next compile. Captured status1
continues; parse/compile/driver errors or fatal target exits stop the process.
Repeated paths have fresh globals/imports/allocator/handler state, not reused
exports. `jitboundary.finish` is shared with the status probe, whose output
and checkpoint protocol remain unchanged. Diagnostic checkpoints prove each
heap/image range disappears before the next cycle, allowing address reuse.
This is not repeated calls into one module, shared objects/GC/function ABI,
resource cleanup, an unbounded memory guarantee or a tier. Existing status
capture restrictions remain. See `docs/jit-sequence-probe.md`.

### Bounded multi-submission console experiment
`std.console` wraps lineedit with1..16 retained submitted lines and a counter;
Enter (even empty) appends, evicts oldest beyond the limit and resets active
line. `feed` returns whether submission occurred. Existing line capacity,
ASCII/control validation and editing rules remain; state is opaque to callers.
`kernel/kconsole_session.holy` renders four42-character recent lines and a
new input line, updating text rows per key, never executing text. Original
single-line demo remains. The freestanding16MiB bump heap still has no
reclamation: bounded transcript length does not bound lifetime allocations,
and a long session can OOM/halt. Six submissions plus seventh editable line
are tested, not indefinite terminal use. No history recall/navigation, shared
agent runtime, command evaluation or Unicode is added. See
`docs/console-session.md` for tests and optional GRUB gate.

### Direct kernel bitmap text
`kernel/kfont.holy` provides draw/fill on a validated mapped RGB24/32
framebuffer descriptor. Draw retains std.font glyph/case/fallback/newline,
scale/text/coordinate/color validation and clipping. Fill validates all
arguments before writes and clips; nonpositive extent writes nothing. It
uses while loops, no materialized rectangle range lists or software RGB
surface. The session console uses this path with unchanged layout. Descriptor
trust/safety is unchanged from kframebuffer. Glyph/string/edit allocations
remain and the16MiB bump heap still cannot reclaim; no zero-allocation,
unbounded-session or performance claim. See `docs/kernel-font.md`.

### Repeated exact-key scalar native calls
`jit_function_probe.holy SOURCE EXACT_IR_KEY JSON_ARGUMENT_SETS` initializes
one isolated native module once and invokes the exact local non-entry code
key for1..32 exact-arity sets of signed30-bit integer arguments. Captures
reject, only tagged integer returns are copied across; non-integer returns
stop without dereferencing/exporting them. The direct key bypasses dynamic
name lookup/rebinding and is not a stable public export or source dispatch.
Per-call shims save C ABI state, update target GC stack boundary, capture
language errors to copied bytes/line and let later calls continue. Target
global/import/heap state persists, including mutations before errors, until
final target heap/image teardown. Init error skips calls. Driver/fatal failures
and unsupported returns do not claim normal teardown. Existing two-argument
prepare/probes retain behavior. No shared objects/GC roots/closure/error
identity, callback ABI, tiers or performance claim. See
`docs/jit-function-probe.md` for transport and fatal/resource restrictions.

### Target-native dynamic global invocation experiment
`jit_dispatch_probe.holy SOURCE GLOBAL_IDENTIFIER JSON_ARGUMENT_SETS` uses a
private native IR wrapper with the compiler's ordinary global-value call
lowering. Unlike exact-code-key calls it reloads the main-module global each
time, honoring rebinding, aliases and target closure captures. No closure or
heap value crosses to the driver. Names are one1..128 ASCII identifier;1..32
same-arity signed30-bit integer sets, integer results only, defaults not added.
Call-site errors use synthetic wrapper line2; target/builtin source-line
semantics otherwise stay unchanged (some builtin errors use0). Root captured
errors permit continuation, target mutations persist, init error skips calls.
Prior scalar/return/sequence protocols remain. This is not a shared runtime,
GC/root/value ABI, public plugin/export API, cold/hot tier or performance
claim. See `docs/jit-dispatch-probe.md` for fatal/resource/transport limits.

### Self-hosted cold scalar IR execution
`selfhost/be/coldscalar.holy` interprets verified IR in .holy without target
machine-code generation. It supports signed30-bit Int, Bool/null, bounded
integer arithmetic/comparison, scalar equality/not, branch/jump/phi, variables/
globals, module-level functions with interpreted dynamic rebinding/recursion,
exact arity, one-scalar print and return. Nested functions, captures, imports,
classes, source objects/strings/floats, division, exceptions/FFI/unsafe/builtins
remain unsupported. Whole-module preflight rejects unknown instructions,
operators, terminators and unsupported constants before effects. Operand/limit
errors can occur after effects and do not roll them back. Locals do not fall
back to globals when unbound. Phi inputs snapshot the predecessor then commit
simultaneously. CLI step limit1M, library1..10M, max64 live frames/256functions,
single-start state, cleanup of call depth on failures; per-function entry counts
are bounded and optionally printed with steps. Executor diagnostics do not yet
match source exception/line semantics. No target hot tier, native transition,
shared GC/value ABI, sandbox, speed or completed-stage claim. See
`docs/cold-scalar.md` for exact restrictions and tests.

### Fixed OS console byte storage
`kernel/kconsole_buffer.holy` is trusted opaque state, separate from graphical
and std.console demos. Capacity1..256, retained1..16; one raw data allocation
and fixed lengths. Feed Int0..255/null: newline submits including empty,
backspace edits, ASCII32..126 appends up to cap, other bytes ignore. Circular
history preserves oldest-first checked address/length access. Reset clears
active length only. Invalid arguments fail before effects. No source container,
string, slice/range or raw allocation in valid feed/reset/access paths after
create. Stale bytes past length remain private/unread. No hostile-state safety,
reclamation, counter-overflow handling, renderer integration or infinite session
claim. See docs/console-buffer.md.

### Cold interpreter-owned flat scalar Lists
The cold executor supports build_list/index/setindex and unshadowed len/append,
with private List/function/builtin records so source Lists cannot masquerade
as callable records. Elements are Int30/Bool/null only. Assignment/pass/return
preserves List identity inside interpreted frames/globals; negative indexing,
truth/not and indexed updates work. No nested/cyclic/source-object elements,
List comparison/printing/slicing or native object sharing is added. Validate
index/element/cap before writes. Limits4096 elements/List,1024 cumulative List
creations,65536 cumulative inserted slots/state, never replenished; stores
replace without new slot. Existing execution limits remain. Hosted executor
GC owns these records; cross-tier roots/values remain unresolved. Ternary
scalar arms work through existing singleton-list lowering. Runtime errors may
follow effects and still lack source exception parity. See `docs/cold-lists.md`.

### Trusted raw-byte kernel font spans
`kfont.draw_bytes` accepts a valid low-memory byte span with length0..1024,
positive address and end<=536870911. Caller supplies live readable memory and
validated framebuffer; this is not pointer validation. Strict integer numeric
arguments/scale1..16/coordinate-color bounds validate before pixel writes.
ASCII newline/case/fallback layout matches existing font, unknown bytes incl
zero render '?', no span copying or glyph-list copying. Valid drawing/fill
uses scalar while loops and statement branches, avoiding ternary singleton
List lowering. Finite QEMU allocation-marker and RGB24/32 guarded pixel oracles
are required. Existing string draw remains; no console integration, GC,
hostile-pointer safety, indefinite lifetime or performance claim.

### Runtime scalar native argument experiment
`jitboundary.prepare_dynamic` creates one native ordinary-global-dispatch shim
with0..6 args. `dynamic_outcome` validates an exact List of Int30 (not Bool)
before copying tagged immediate words to target writable argument slots; one
unchanged entry reloads them on every call. Runtime-computed later arguments
work. Invalid transports leave slots/native state untouched; root-native error
outcomes permit later calls without rollback. Existing init-before-call and
heap-then-image release protocol remains trusted/caller-owned, nonconcurrent
and nonreentrant. Dead images reject. No code mutation, object/exception/root
sharing or cold/hot tier. Existing fixed-set APIs retained. Diagnostic CLI
1..32 calls validates later sets at invocation time, not before init/earlier
effects. See docs/jit-dynamic-arguments.md for fatal and lifecycle restrictions.

### Fixed byte console demo integration
`kernel/kconsole_fixed.holy` connects fixed42-byte/four-line history storage
and raw-byte framebuffer font rendering. Display only, no command evaluation.
Old string demos remain. readkey still allocates32bytes/consumed byte and the
16MiB bump heap has no reclamation. Static string labels and logging are outside
finite allocation proof. Actual QEMU1000 storage+redraw cycles must show16byte
marker gap (only marker allocation) plus independent guarded RGB32 pixels;
optional actual GRUB six-submission CDEF/currentG visual gate required locally.
No infinite-terminal, total session zero-allocation, GC, hardware or speed claim.

### Explicit cold/native immediate scalar bridge
A trusted pre-start host binding may supply a callback/context record to the
cold executor. Normal source globals can shadow it. Calls validate all args
Int30 (no Bool/object), count at most4096 attempts per binding, invoke handler
and require Int30 result. `coldnative` adapts one initialized isolated native
runtime/global shim: only immediate words copy, native state/GC remain separate.
Interpreted computation resumes after native return. Native language errors
become copied diagnostics, not shared exception identity; cold depth unwinds,
prior effects persist. CLI preflights cold before native init, releases native
heap/image on controlled exit. Trusted library owns lifecycle; fatal/unsafe/
nonreturning code outside recovery. No native->cold callback, concurrency,
shared object/root ABI, hotness/dispatch replacement, tiering or speed claim.
See docs/cold-native.md.

### Kernel queued keyboard Int input
`readkey_code()` is xkernel-only/direct-call/no args: consume the same queued
translated byte as readkey, return Int1..255 or null when empty, preserve caller
IF and allocate no Str. Queue63/drop-newest/singleCPU and PS/2 translation limits
unchanged, zero sentinel not delivered. readkey stays compatible. Fixed-byte
console demo now uses code input directly. Deterministic IR/AST FIFO+allocation
markers, seed-native full image/100000empty polls and actual local GRUB visual
keyboard gate required. Not hosted/first-class, no generalGC/indefiniteterminal/
totalinteractivezeroalloc/perf/hardware claim. See docs/keyboard-code.md.

### Cold bounded ASCII text
Cold constants may be Str of printable ASCII/newline/tab/return, max1024bytes;
other text constants preflight-reject before effects. Immutable assignment/pass/
return, Str+Str, same-type equality/order, truth/not/shortcircuit, len, negative
Int indexing and one-value print work. Mixed types/repetition/slicing/iteration/
methods/Unicode/string List elements remain outside subset; string ternary arms
reject through existing singleton-list lowering. Per-state logical text budget
65536bytes cumulative: const execution charges length, concatenation full result,
index one. No refunds; aliases/pass/print/len/compare no added charge. Validate
before allocation/accounting; not exact heap/parser/temporary storage bound.
FlatList/nativeInt-only boundaries unchanged. No sharednativeGC/hot/perfclaim.
See docs/cold-text.md for runtime/preflight limits.

### Cold text elements in flat Lists
Cold flatList literal/append/store accepts existing bounded ASCII Str alongside
Int30/Bool/null. Mutable List aliases preserve identity; retrieved text aliases
remain immutable after replacement. Existing text production and List creation/
slot budgets stay separate: referencing text in slots adds no byte charge,
replacement no slot charge. Validate before mutation. String ternary arms now
work with lazy singletonList lowering; List-valued arms still reject nested
Lists. Nested/cyclic/function objects, List comparison/print, native transport
of objects remain unsupported. See docs/cold-text-list.md.
