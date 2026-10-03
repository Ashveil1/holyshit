# editor support

ทุกตัวชี้ไปที่ `lsp.py` เดียวกัน (stdio, ไม่มี dependency)

| editor | โฟลเดอร์ | วิธีติดตั้ง |
|---|---|---|
| VS Code | `vscode/` | เปิดโฟลเดอร์นี้ในโค้ด → F5 |
| Neovim | `neovim/` | `runtimepath:append(...)` + `require('holyshit').setup{}` |
| Helix | `helix/` | เพิ่ม `[language-server.holyshit]` ใน `languages.toml` |
| Zed | `zed/` | `[language_servers."holyshit-lsp"]` ใน `settings.json` |

ฟีเจอร์ที่ได้ทั้งหมด: diagnostics, hover, completion,
goto definition (ข้ามไฟล์ได้), document symbols, formatting
