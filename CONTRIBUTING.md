# contributing to holyshit

A small language written and tested in pure Python (no dependencies) - both
humans and AI agents are welcome to help.

## Where to start

| I want to | File |
|---|---|
| Write language/docs for humans | `docs/index.md` -> `docs/for-agents.md` |
| Change semantics | `interp.py` (the reference of truth), then make backends match |
| Change the native backend (gcc) | `hs.py` + `native/rt.{h,c}` |
| Change the x86-64 backend | `x64.py` (assembler) + `x64gen.py` (codegen + runtime) |
| Change the formatter | `fmt.py` |
| Change the LSP | `lsp.py` |
| Change generated tools/docs | `scripts/lang_data.py`, `scripts/gen_*.py` |

## setup

```sh
python3 --version          # 3.8+ with nothing to pip install
python3 hs.py check prog.holy
python3 tests/run_all.py   # --quick skips the qemu parts
```

The kernel tests need `qemu-system-x86_64`; without it they print `skip`.

## Test rules (important)

1. Every `.holy` needs an `.expected` (stdout) or a `.fail` (expected error line)
2. `interp.py` is the truth - if native/x64 differ from interp, **the differing one is wrong**
3. After adding tests run `tests/test.py` + `tests/test_native.py` (+ `test_x64.py`
   for subset code) - never reduce the existing test count
4. Touching a builtin/error/doc -> run `scripts/gen_api.py` / `scripts/gen_errors.py`
   then `tests/test_docs.py` (it catches drift for you)
5. Changing an external `.holy` -> `python3 hs.py fmt <file> -w` before committing
   (`--check` ignores comments/blank lines; the test verifies the whole repo is canonical)
6. Code in ```hs blocks inside `docs/*.md` **actually runs** in the test suite -
   never write an example that does not pass

## style

- Python: 4 spaces, snake_case function/variable names, no unnecessary type hints
- f-strings are fine, but user-facing error messages must be identical across backends
- Docs are written in English
- Commits may be short, but say "what changed / why / what it affects"

## A good commit (real example from history)

```
fix: x64/kernel skip finally when the except handler raises

Fix in x64gen.ex_try: guard the handler with another hs_try_push0 layer - an
error in the handler now jumps to finally first, then hs_reraise continues
outward

Tests: tests/x64/try.holy, kernel/ktry.holy
```

## Adding a new builtin

1. Add it in `interp.py` (`BUILTINS` + a `b_*` function)
2. If hosted-only, add it in `hs.py` (BUILTINS + `native/rt.c`)
3. If it works on x64, add it in `x64gen.py` + `native/rt.c` (when hosted)
4. Update `scripts/lang_data.py` (sig/desc/backend) - `tests/test_docs.py`
   checks it is complete and matches `interp.BUILTINS`
5. Run `scripts/gen_api.py` + `scripts/test*.py`

## AI agents

Always read `AGENTS.md` first, then use `scripts/lsp_client.py` instead of
guessing: `--diag` gives the line, `--refs` every call site, `--def` jumps to
the definition. `AGENTS.md` must stay short and correct - if a rule gets too
long, move it to `docs/`
