# holyshit LSP (`lsp.py` + `hs.py lsp`)

A language server over stdio (JSON-RPC, nothing extra to install).
Run it with `python3 hs.py lsp` or `python3 lsp.py` directly.

## Capabilities

| Feature | How |
|---|---|
| diagnostics | parse + scope check on every open/edit/save (lines match `hs.py check`) |
| hover | builtin (signature + backends), keyword, def/param/variable, `mod.attr` (shows the defining file) |
| completion | keyword + builtin + in-file names; after `mod.` offers only the module's top-level names |
| goto definition | in-file + cross-file (`mod.attr`, `import mod`, re-exported submodules) |
| references | every call site across files in the same directory + `HSPATH` (declarations included) |
| document highlight | every occurrence of the name on that line + its declaration line |
| signature help | both user `def`s and builtins (`activeParameter` follows commas) |
| document symbols | file-level `def` / variables / imports |
| workspace symbols | search names across the whole project |
| formatting | `hs fmt` for the whole file |

Known limitations: multiple references on one line resolve to the occurrence
nearest the cursor; hover/completion do not know types (dynamic language).

## Connecting an editor

VS Code (`editors/vscode/`): open that folder in VS Code and press F5
(the extension runs `python3 <repo>/lsp.py` itself, no `npm install`).
Neovim (`editors/neovim/`): ships `editors/neovim/syntax/hs.vim` + a `vim.lsp.start` example:

```lua
vim.lsp.start({ name = "holyshit", cmd = {"python3", "/path/to/holyshit/lsp.py"} })
```

Helix/Zed: point the language server at the same command
(`editors/helix/README.md`, `editors/zed/README.md`)

## Use from an AI agent (no long-lived server)

`scripts/lsp_client.py` starts a temporary server per command:

```sh
python3 scripts/lsp_client.py --diag prog.holy
python3 scripts/lsp_client.py --hover prog.holy 3 5     # line/col start at 1
python3 scripts/lsp_client.py --complete prog.holy 1 4
python3 scripts/lsp_client.py --def prog.holy 2 10
python3 scripts/lsp_client.py --refs prog.holy 2 10     # project-wide references
python3 scripts/lsp_client.py --highlight prog.holy 2 10
python3 scripts/lsp_client.py --sig prog.holy 4 9       # signature help
python3 scripts/lsp_client.py --wsym prog.holy double   # workspace symbols
python3 scripts/lsp_client.py --symbols prog.holy
python3 scripts/lsp_client.py --format prog.holy [--write]
```

Known limitation: references/workspace symbols scan `.holy` files in the
opened file's directory (skipping `.git`, `legacy`, `__pycache__`) plus
`HSPATH` - so it is not yet a full workspace index, but enough for projects
whose `.holy` files live together.
