# holyshit VS Code extension

No `npm install` needed - `client.js` spawns `python3 ../../lsp.py` itself
(if `vscode-languageclient` is installed it will be used)

## Use

1. Open `editors/vscode/` in VS Code
2. `npm run dev:install` (once - installs the `holyshit` extension) or press F5
   to open an Extension Development Host
3. Open a `.holy` file -> diagnostics/hover/completion/goto work immediately

Point at another python via env:

```sh
HS_PYTHON=/usr/bin/python3.12 code editors/vscode
```

## Files

- `package.json` - contributes the `holyshit` language + restart/check commands
- `language-configuration.json` - `#` comments, `:`-based indent, brackets
- `client.js` - the LSP glue (stdlib + `vscode-languageclient` when present)

## Using it with another project

Associate `.holy` with the LSP directly in the project's `settings.json`:

```json
{
  "files.associations": { "*.holy": "holyshit" },
  "holyshit.serverPath": "/path/to/holyshit/lsp.py"
}
```
