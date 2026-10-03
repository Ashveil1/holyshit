# Helix — holyshit

Helix เป็น LSP client อยู่แล้ว จึงแค่ชี้ language server:

```sh
# ~/.config/helix/languages.toml
[language-server.holyshit]
command = "python3"
args = ["/path/to/holyshit/lsp.py"]

[[language]]
name = "holyshit"
scope = "source.holyshit"
file-types = ["hs"]
comment-token = "#"
indent = { increment = "  " }
language-servers = ["holyshit"]
```

เสร็จแล้ว: `:language-server restart`, hover (`h`), completion (`ctrl-x`),
goto (`gd`), format (`=` ถ้าเซิร์ฟเวอร์รองรับ), diagnostics ใต้บรรทัด

ถ้าอยากมี syntax สีตามชัด ใส่ไฟล์ queries ของภาษาอื่น (Rust/Python)
แล้ว map `source.holyshit` ไปที่มัน:

```toml
[[grammar]]
name = "holyshit"
source = { path = "/path/to/holyshit/editors/tree-sitter-holyshit" }
file-types = ["hs"]
```
