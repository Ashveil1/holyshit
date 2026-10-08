# IR Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the direct AST→machine-code path in `x64gen.py` with an architecture-neutral IR (`ir.py`) that every backend (x86-64 now, ARM64 later, JIT later) consumes.

**Architecture:** `interp.py` stays the parser + reference semantics. New `ir.py` builds a flat CFG (basic blocks, SSA temps, explicit `phi`) from the AST, verifies it, and runs it on a reference interpreter that must be byte-identical to `interp.py`. Backends become IR→machine-code lowerers; they never read AST again.

**Tech Stack:** Python (host), existing `x64.py` assembler, QEMU for kernel/ARM tests.

**Spec:** `SPEC-v1.md` §15.34 (v0.6.20 baseline); OS-ready requirements in `docs/kernel.md`.

## Global Constraints

- Every milestone keeps all suites green (`python3 tests/run_all.py`), then its own commit on `main`.
- Error strings that must appear in `docs/errors.md` stay literal / string-concat, never f-strings; then run `scripts/gen_errors.py` / `scripts/gen_api.py`.
- `hs fmt -w` strips comments — never run `-w` on a commented `.hs` file.
- x64 `and`/`or` do not short-circuit (documented divergence in `docs/x64-subset.md`); IR lowers `and`/`or` to branch+phi (short-circuit), so the x64 backend must grow real branches when it moves to IR.
- 62-bit Int on x64 vs 64-bit on interp is an accepted divergence; IR is bit-width-agnostic (backends own `wrap_i64`).

---

### Task 1: IR core — build, verify, print, execute (TONIGHT)

**Files:**
- Create: `ir.py`
- Create: `tests/test_ir.py`
- Modify: `tests/run_all.py` (add suite + count)
- Modify: `SPEC-v1.md` (append §15.35), `AGENTS.md` (2-line IR note), `README.md` (suite list), `VERSION`

**Interfaces:**
- Consumes: `interp.parse_program(src) -> [stmt]`, `interp.HSErr`, `interp.disp`, `interp.BUILTINS`, `interp.wrap_i64/is_num/is_int` — exact names from `interp.py`.
- Produces: `ir.build_module(prog) -> Module`; `ir.verify_module(m) -> None (raises HSErr)`; `ir.run_module(m, argv) -> int exit code`; `ir.dump_module(m) -> str`.

- [ ] **Step 1: Write `tests/test_ir.py` (differential: `ir.py` vs `interp.py` on inline programs)**

```python
import subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASES = [
    ("arith", "print 1 + 2 * 3\nprint 7 / 2\nprint 7 % 3\n", "7\n3.5\n1\n", "", 0),
    ("fib", "def fib(n):\n  if n < 2:\n    return n\n  return fib(n - 1) + fib(n - 2)\nprint fib(10)\n", "55\n", "", 0),
    ("divzero", "print 1 / 0\n", "", "error: division by zero at line 1\n", 1),
]
fails = 0
for name, src, want_out, want_err, want_rc in CASES:
    with open(f"/tmp/ir_{name}.hs", "w") as f:
        f.write(src)
    a = subprocess.run([sys.executable, f"{ROOT}/interp.py", f"/tmp/ir_{name}.hs"], capture_output=True, text=True)
    b = subprocess.run([sys.executable, f"{ROOT}/ir.py", f"/tmp/ir_{name}.hs"], capture_output=True, text=True)
    ok = (a.stdout == b.stdout == want_out and a.stderr == b.stderr == want_err and a.returncode == b.returncode == want_rc)
    print(("ok  " if ok else "FAIL") + f" {name}")
    fails += 0 if ok else 1
print(f"{len(CASES) - fails}/{len(CASES)} passed")
sys.exit(1 if fails else 0)
```

- [ ] **Step 2: Run it, watch it fail**

Run: `python3 tests/test_ir.py`
Expected: FAIL with "No such file or directory" / `ir.py` missing.

- [ ] **Step 3: Write `ir.py` (minimal to pass)**

Subset: `num str var bin(not/and/or/neg/unot/cmp/arith/bitwise) call print set def return global if/elif/else while break continue pass`. Everything else raises `HSErr("IR: unsupported '<t>'", line)`.
Shapes (plain dicts, same style as `interp.N`):
`Func {"name","params","blocks","entry"}`; `Block {"label","instrs","term"}`;
instrs: `const{dest,val}` `mov{dest,src}` `bin{dest,op,l,r}` `un{dest,op,v}` `call{dest,fn,args}` `print{args}` `phi{dest,arms:[(label,temp)]}` `load{dest,name}` (runtime scope lookup for forward refs) `mkfunc{dest,name}`;
terms: `jmp{to}` `br{cond,then,els}` `ret{val}`. Every instr/term carries `line`.
Reference interpreter mirrors `interp.ev/ev_bin/ex` messages exactly (reuse `disp`, `BUILTINS[name].fn`, `wrap_i64/is_num/is_int`).

- [ ] **Step 4: Extend CASES to ~16 programs (control flow, closures, short-circuit guards, error parity) and pass**

Add: `if/elif/else`, `while`+`break`/`continue`, nested while, early return, closure capture, `global`, `true or 1/0` (no error), `0 and 1/0` (prints 0), `unknown variable 'y'`, arity mismatch, `cannot add Int and Str`, bitwise/shift, chained `1 < 2 < 3`, float shortest repr (`print 0.1`), builtin `len/str/int`.
Expected: `16/16 passed`, stdout/stderr/rc byte-identical to interp on every case.

- [ ] **Step 5: Verifier unit tests inside `tests/test_ir.py`**

Hand-built bad modules must raise: duplicate block label, jump to missing label, use of undefined temp, phi arm from non-predecessor. Builder must raise `IR: unsupported` for `for`/`import`/`try`/`unsafe`.

- [ ] **Step 6: Wire suite + docs + commit**

Run: `python3 tests/run_all.py --quick`
Expected: all suites pass including new `test_ir.py`.
Then append `SPEC-v1.md` §15.35, update `AGENTS.md`/`README.md`/`VERSION` (0.6.21), commit on `main`.

### Task 2: Containers + `for` in IR (DONE v0.6.22)

Lower `list/dict/index/slice/setindex/for` (desugar `for` to len/index/while over a private temp). Differential-test against `tests/*.hs` container programs. `setattr/attr` (module attrs) stay AST-side until Task 4.

### Task 3: Dominance verifier + IR text format (DONE v0.6.23)

Proper def-dominates-use check; `hs.py ir prog.hs` dumps canonical IR text; round-trip parse test. Needed before backends consume IR.

### Task 4: x64 backend consumes IR (part 1 DONE v0.6.24, part 2 DONE v0.6.25)

Rewire `x64gen.py` entry to `ir.build_module` + lower IR (real branches for `and`/`or` — kills the short-circuit divergence). Full `tests/test_x64.py` green unchanged. `interp.parse_program` remains only for `check`/`fmt`.

### Task 5: ARM64 backend on IR (Linux userspace first, then freestanding)

New `arm64.py` assembler (ELF64, own relocations) + `armgen.py` IR lowerer. QEMU `qemu-aarch64` differential suite `tests/test_arm64.py`. Then freestanding ARM64 (`xkarm`: UART, GIC, MMU tables) reusing kernel IR.

### Task 6: OS-ready IR extensions

`unsafe:` blocks, volatile MMIO (`load8/store8` + `volatile` marker backends must not fold), interrupt/task entry points, `image_end`/linker-provided symbols as IR constants. Kernel test suite runs through IR unchanged.

## Self-Review

- Spec coverage: Task 1 covers "IR exists and is semantics-preserving" (the tonight claim). Tasks 2–6 each map to one roadmap phase from the approved estimate (containers → dominance → x64 → ARM → OS-ready). No task without an owner phase.
- Placeholder scan: no TBD/TODO; every step names exact files, function names (`build_module`, `verify_module`, `run_module`, `dump_module`), and exact commands.
- Type consistency: IR node shapes defined once in Task 1 Step 3 and reused by Tasks 3–6 verbatim.
