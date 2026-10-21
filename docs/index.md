# holyshit docs - start here

A dynamic language that is as easy to write as Python, with 4 run targets
(see the table in `builtins.md` for which feature runs where). The docs are
written for humans, for AI agents and for machines - and every claim in them
is checked by tests.

| I want to... | Read |
|---|---|
| Install and run/build natively (Linux x86-64) | [native-install.md](native-install.md) |
| **One-page cheatsheet** | `cheatsheet.md` |
| Write my first program in 10 minutes | `tutorial.md` |
| See runnable examples | `../examples/` |
| Look up a builtin/keyword (human) | `builtins.md` |
| Find out what an error means | `errors.md` |
| Write my own `std.*` / use std | `stdlib.md` |
| Run without gcc / go bare metal | `x64-subset.md`, `kernel.md` |
| Hook up an editor / let AI drive the language | `lsp.md`, `for-agents.md` |
| Let a program read the language (JSON) | `api.json` |
| Design rationale + phase history | `../SPEC-v1.md` |
| The most compact rules | `../AGENTS.md` |
| Help extend/fix the language | `../CONTRIBUTING.md` |

## Normal install/run/build (Linux x86-64)

```sh
sh scripts/install-native.sh "$HOME/holyshit-native"
"$HOME/holyshit-native/bin/hs" run examples/hello.holy
"$HOME/holyshit-native/bin/hs" build examples/hello.holy /tmp/hello-hs
```

Use a new directory with an existing parent. No Python/gcc is needed for
this route; shell/checksum utilities and host libc/shared libraries are
required. The installed launcher supports run/build of the hosted subset,
not all development commands or the entire language. See
[native install](native-install.md) for relocation, updates and limits.

## Development/reference tools (Python)

```sh
python3 interp.py prog.holy     # tree-walk, reference behavior
python3 hs.py check prog.holy   # syntax/scope check only
python3 hs.py build prog.holy   # native binary via gcc
python3 hs.py xbuild prog.holy  # direct machine code, no gcc
python3 hs.py xkernel prog.holy -o k.elf  # kernel that boots in QEMU
python3 hs.py lsp             # language server (stdio)
```
