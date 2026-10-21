# holyshit (hs) — v0.6.30

A dynamic language that is as easy to write as Python, runs in 4 modes, calls
C, boots on bare metal, self-hosts its own compiler, and ships a language
server for editors and AI agents.

## Install and run (Linux x86-64)

The normal run/build route is the audited native bundle. From this checkout,
install into a **new directory** whose parent already exists:

```sh
sh scripts/install-native.sh "$HOME/holyshit-native"
"$HOME/holyshit-native/bin/hs" run examples/hello.holy
"$HOME/holyshit-native/bin/hs" build examples/hello.holy /tmp/hello-hs
/tmp/hello-hs
```

No Python or gcc is needed to install or use this route. It needs Linux
x86-64, `/bin/sh`, standard shell/checksum utilities and host libc/shared
libraries for FFI. Installation builds the eager driver once and can take
time. Move the whole installed directory together; no checkout is needed
after installation. The installer does not edit PATH/shell profiles, use sudo
or overwrite an existing directory. Use a new directory for each update;
keep the old one until the new version is checked. Removing an install means
removing only its chosen directory, not any source checkout.

The native launcher currently provides only `run SOURCE [args...]` and
`build SOURCE OUTPUT`. It reports unsupported hosted-subset programs rather
than silently falling back. It does not provide the Python CLI's check, fmt,
test, REPL, LSP or kernel commands. `run` compiles eagerly in memory, not on
first call or in tiers. The installed prebuilt driver is not rebuilt per run.
See [native install details](docs/native-install.md).

## Experimental in-memory JIT (Linux x86-64)

An eager in-process JIT driver, with the emitter written in holyshit itself
(no LLVM, no external libraries), is available for experiments:

```sh
scripts/run-jit-native.sh tests/fib.holy
```

It compiles source to machine code, relocates it into owned RX mappings and
executes it in the same process, with a persistent compiled-code cache.
There is no first-call compilation, tiering, type feedback or deopt yet.
See [docs/jit.md](docs/jit.md).

## Development and reference tools (Python)

These remain available for independent semantic checks, diagnostics, editor
support and development. They are not required by the installed run/build
route. Their backend behavior differs from the native launcher:

```sh
python3 interp.py prog.holy [args...]   # run immediately (tree-walk)
python3 hs.py check prog.holy           # syntax/scope check only
python3 hs.py build prog.holy [-o prog] # native binary (gcc + Boehm GC)
python3 hs.py run prog.holy [args...]   # build to temp then run (default: x64, no gcc, own fallback)
HS_BACKEND=auto|x64|native|interp     # pick the run backend (or run prog.holy --backend X)
python3 hs.py fmt prog.holy [-w|--check] # canonical format (2-space, strips comments)
python3 hs.py test file_or_dir...      # run every `def test_*()` (assert = test); --json for agents, exit 1 on failure
python3 hs.py repl                       # REPL: state persists across lines, bare expressions print, errors don't quit
python3 hs.py run selfhost/cc.holy prog.holy out   # the compiler written in hs itself: Int/def/while/print -> ELF x86-64 (see tests/test_cc.py)
python3 hs.py xbuild prog.holy [-o prog] # direct machine code, no gcc (subset)
python3 hs.py xkernel prog.holy -o k.elf # freestanding kernel, no gcc/as/ld
python3 hs.py lsp                     # language server (stdio, no dependencies)
python3 hs.py --version
```

Start reading at **[`docs/index.md`](docs/index.md)** - cheatsheet, tutorial,
runnable examples, stdlib, x64 subset, kernel, LSP, and a guide for AI agents.

## 30-second example

```
def fib(n):
  if n < 2:
    return n
  return fib(n - 1) + fib(n - 2)

print fib(10)

extern from "m":
  F64 sin(F64 x)

print sin(0.0)
```

## Project layout

| Part | File |
|---|---|
| All documentation (start here) | `docs/index.md` |
| Rules for AI agents | `AGENTS.md` |
| Language spec + design rationale | `SPEC-v1.md` |
| Contributing | `CONTRIBUTING.md` |
| interpreter (reference behavior) | `interp.py` |
| native backend (AST->C->gcc) + CLI | `hs.py` + `native/rt.{h,c}` |
| direct x86-64 backend (subset, no gcc, tagged values) | `x64.py` + `x64gen.py` |
| self-hosted compiler (written in hs) | `selfhost/` (entry: `selfhost/be/compile.holy`) |
| pinned bootstrap seed (compiles itself, fixed point) | `bootstrap/` |
| experimental in-memory JIT driver | `selfhost/be/jit_run.holy` + `docs/jit.md` |
| kernel runtime (freestanding) | `kernel/` |
| standard library (written in hs) | `std/` |
| language server (diagnostics/hover/goto/format) | `lsp.py` + `editors/` |
| machine-readable language data | `docs/api.json`, `docs/errors.md`, `scripts/lang_data.py` |
| topic examples | `examples/` |
| benchmarks (hs vs CPython) | `bench/` + `docs/bench.md` |
| tests | `tests/` |
| old v0.3 (WASM) | `legacy/` |

## Language highlights

See `SPEC-v1.md` for the full story - easiest to hardest:
`examples/hello.holy` -> `fib.holy` -> `closure.holy` -> `ffi.holy`

- dynamic types: Int Float Str Bool Null List Dict Func (+ first-class)
- `def if/while/for try/except import` - Python-style indentation
  (dotted `import std.str` works, std lives in `std/`)
- `unsafe:` - I64/U64/Ptr + inline `asm` (a static subset in the same language)
- `extern [from ...]:` - call C/.so/anything through the C ABI
- closures (copy semantics), JSON, socket/HTTP client, argv/env/system
- an x64 subset that runs with no gcc at all (including the kernel) - full
  Int/Float/Str/List/Dict/Bool/Null, `- * / %` float arithmetic and
  `print`/`float()` with shortest round-trip matching Python without libc,
  `json_parse`/`json_str` (compiled from `runtime/json.holy` into the image)

## Tests

```sh
python3 tests/run_all.py         # everything (skip kernel with --quick)
python3 tests/test.py          # interpreter (85 cases)
python3 tests/test_native.py   # native binary (results must match interp)
python3 tests/test_fmt.py      # formatter (canonical+idempotent+exec+whole repo)
python3 tests/test_x64.py      # direct x86-64 backend (143, static ELF)
python3 tests/test_ir.py       # middle IR: build/verify/exec matches interp byte for byte (179)
python3 tests/test_irx64.py    # IR->x64 vs the old path (73, ELF vs ELF)
python3 tests/test_be.py       # hs-written backend vs Python emitter, byte-identical (65)
python3 tests/test_jit_corpus.py # JIT corpus parity (85)
python3 tests/test_hosted_seed.py # pinned bootstrap seed checks
python3 tests/test_xkernel.py  # freestanding kernel, real QEMU boots (291 cases)
python3 tests/test_examples.py # every example file still runs
python3 tests/test_lsp.py      # language server over stdio (25 cases)
python3 tests/test_docs.py     # docs: tutorial code really runs + links + api.json (85)
```

Test rules: `tests/<name>.holy` + `.expected` (stdout), `.stdin` (input),
`.args` (argv line by line), `.env` (KEY=VAL per line), `.fail` (expected
error, matched against stderr), `mod_*` = helper (not run directly),
`.nativeonly` = skip the interp side.

## editor

The language server is pure stdio with nothing to install - point your editor
at `python3 <repo>/lsp.py` (VS Code / Neovim / Helix / Zed examples in
`editors/`)

```sh
python3 hs.py lsp                                  # server
python3 scripts/lsp_client.py --diag prog.holy       # one-shot command (for agents)
```

## for AI agents

Read `AGENTS.md` before writing `.holy` - a compact reference with all the
rules, gotchas and the fix loop (`check` -> `interp` -> `build`, errors with
`--json`). A shorter version is `docs/for-agents.md`.

## License

Apache License 2.0 - see `LICENSE`. Copyright 2026 Ashveil1.
