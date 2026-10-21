# for agents - write `.holy` fast and unbroken

The full rules live in `../AGENTS.md` (read before writing code). This page is
the shortcut plus the tools an agent can call right away.

## Writing a program (no guessing)

```sh
python3 hs.py check prog.holy    # 1. fast syntax + scope (does not run)
python3 hs.py run prog.holy      # 2. build with gcc then run
python3 interp.py prog.holy     # 3. reference behavior (slower, but the truth)
python3 tests/test.py          # 4. the whole suite
```

All 4 commands accept `--json` -> errors become
`{"file":...,"line":...,"message":...}` on stderr so you can fix the exact line:

```sh
python3 hs.py --json check prog.holy
```

## Adding a new test case

Write `tests/<name>.holy` + `tests/<name>.expected` (correct stdout)
or `tests/<name>.fail` (expected error line) if the case should fail.
Add `tests/<name>.args` / `.stdin` / `.env` as needed, then run:

```sh
python3 tests/test.py          # interp (85)
python3 tests/test_native.py   # native binary, must match interp
python3 tests/test_x64.py      # direct x86-64 backend (143)
python3 tests/test_xkernel.py  # real QEMU boot (needs qemu-system-x86_64)
python3 tests/test_lsp.py      # LSP protocol (25)
```

A `.holy` with `import` is skipped on x64 when the module is outside the
subset - the test will tell you.

## Self-help tools (one-shot LSP)

```sh
python3 scripts/lsp_client.py --diag prog.holy          # error + line
python3 scripts/lsp_client.py --symbols prog.holy       # def/vars in the file
python3 scripts/lsp_client.py --hover prog.holy 3 5     # builtin/keyword/var
python3 scripts/lsp_client.py --def prog.holy 2 10      # jump to definition
python3 scripts/lsp_client.py --complete prog.holy 1 4  # keyword+builtin+file names
python3 scripts/lsp_client.py --refs prog.holy 2 10     # every call site (cross-file)
python3 scripts/lsp_client.py --sig prog.holy 4 9       # signature of the call here
python3 scripts/lsp_client.py --wsym prog.holy name    # search a name project-wide
python3 scripts/lsp_client.py --format prog.holy --write  # rewrite canonical
```

(line/col start at 1 - human-friendly)

## The same data for programs to read

```sh
python3 scripts/gen_api.py     # rewrites docs/api.json + docs/builtins.md
python3 scripts/gen_errors.py  # rewrites docs/errors.md (from source)
```

`docs/api.json` = keywords + builtins (sig/desc/supported backends)
`docs/errors.md` = every error message in the language + a table of common ones
`scripts/lang_data.py` = the shared source used by the LSP and the tests

## Traps that break tests most often

1. `//` is always a comment - there is no `//` division (use `/`)
2. No `;` `{` `}` in the language
3. `for i in 0..5` does not exist - use `range(5)`
4. `print (1+2)*3` breaks - write `print ((1+2)*3)`
5. Unsure what an error means -> grep `docs/errors.md` (it has every message)
6. Every error looks like `error: <msg> at line N` (stderr, exit 1)
7. `print x, y` is space-separated + trailing newline - not Python print separators
8. Tests that need files/argv/stdin need `.args`/`.stdin` too,
   and never use absolute paths

## What code can go where

| Work | Where |
|---|---|
| General scripts / new stdlib (`std/*.holy`) | interp + native (all features) |
| Must run without gcc | x64 subset (`hs.py xbuild`) |
| kernel / OS | x64 subset + `unsafe:` + `xkernel` |
| Call C / other languages | `extern:` (hosted only) |

See the detailed scope in `x64-subset.md` and `../AGENTS.md`
