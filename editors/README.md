# editor support

All editors point at the same `lsp.py` (stdio, no dependencies)

| editor | folder | how to install |
|---|---|---|
| VS Code | `vscode/` | open this folder in VS Code -> F5 |
| Neovim | `neovim/` | `runtimepath:append(...)` + `require('holyshit').setup{}` |
| Helix | `helix/` | add `[language-server.holyshit]` to `languages.toml` |
| Zed | `zed/` | `[language_servers."holyshit-lsp"]` in `settings.json` |

Features you get everywhere: diagnostics, hover, completion,
goto definition (cross-file), document symbols, formatting
