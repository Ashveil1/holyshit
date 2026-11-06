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

Local file URIs are decoded once and returned locations are URI-escaped, so
projects in folders containing spaces, `#`, `%`, `?`, or Unicode work with
editor navigation. Empty authority and `localhost` are supported; remote
file authorities are not mapped to local paths.

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

References and workspace symbols scan `.holy` and legacy `.hs` files under
an initialized local `rootUri` (or legacy absolute `rootPath`), plus `HSPATH`.
`rootUri` takes precedence and uses the same local-file URI rules as navigation.
Without a root, the opened file's directory is the fallback. Workspace symbols
also work before a file is opened; without any scan source they return `[]`.
Open buffers take priority over disk files. Hidden directories, `legacy` and
`__pycache__` are skipped; directory symlinks are not followed. Discovery keeps
the existing scan cutoff (disk discovery stops after the document list exceeds
400 entries; already-open buffers are retained) and
returns at most 500 symbols. This is not a persistent workspace index.
Multi-root `workspaceFolders` and workspace-folder changes are not supported;
no workspace-folder capability is advertised. The one-shot client still uses
the opened file's directory rather than guessing a project root.
