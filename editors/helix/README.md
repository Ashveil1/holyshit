# Helix - holyshit

Helix is already an LSP client, so just point it at the language server:

```sh
# ~/.config/helix/languages.toml
[language-server.holyshit]
command = "python3"
args = ["/path/to/holyshit/lsp.py"]

[[language]]
name = "holyshit"
scope = "source.holyshit"
file-types = ["holy", "hs"]
comment-token = "#"
indent = { increment = "  " }
language-servers = ["holyshit"]
```

Done: `:language-server restart`, hover (`h`), completion (`ctrl-x`),
goto (`gd`), format (`=` if the server supports it), diagnostics under the line

For real colored syntax, add queries from another language (Rust/Python)
and map `source.holyshit` to it:

```toml
[[grammar]]
name = "holyshit"
source = { path = "/path/to/holyshit/editors/tree-sitter-holyshit" }
file-types = ["holy", "hs"]
```
