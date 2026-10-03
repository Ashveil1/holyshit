# holyshit LSP (`lsp.py` + `hs.py lsp`)

language server ผ่าน stdio (JSON-RPC, ไม่ต้องลง lib เพิ่ม).
รันด้วย `python3 hs.py lsp` หรือ `python3 lsp.py` ตรง ๆ

## ความสามารถ

| ฟีเจอร์ | วิธี |
|---|---|
| diagnostics | parse + scope check ทุกครั้งที่เปิด/แก้ไฟล์ (line ตรง `hs.py check`) |
| hover | builtin (signature + backend), keyword, def/param/ตัวแปร |
| completion | keyword + builtin + ชื่อในไฟล์ |
| goto definition | ในไฟล์ + ข้ามไฟล์ (`mod.attr`, `import mod`) |
| document symbols | `def` / ตัวแปร / import ระดับไฟล์ |
| formatting | `hs fmt` ทั้งไฟล์ |

ข้อจำกัดที่รู้แล้ว: อ้างอิงหลายจุดในบรรทัดเดียวใช้ occurrence ใกล้เคอร์เซอร์;
hover/completion ไม่รู้ type (ภาษา dynamic)

## ต่อ editor

VS Code (`editors/vscode/`): เปิดโฟลเดอร์นั้นใน VS Code แล้วกด F5
(extension เรียก `python3 <repo>/lsp.py` เอง ไม่ต้อง `npm install`).
Neovim (`editors/neovim/`): มี `editors/neovim/syntax/hs.vim` + ตัวอย่าง `vim.lsp.start`:

```lua
vim.lsp.start({ name = "holyshit", cmd = {"python3", "/path/to/holyshit/lsp.py"} })
```

Helix/Zed: ชี้ language server มาที่คำสั่งเดียวกัน
(`editors/helix/README.md`, `editors/zed/README.md`)

## ใช้จาก AI agent (ไม่ต้องค้าง server)

`scripts/lsp_client.py` เปิด server ชั่วคราวต่อหนึ่งคำสั่ง:

```sh
python3 scripts/lsp_client.py --diag prog.hs
python3 scripts/lsp_client.py --hover prog.hs 3 5     # line/col เริ่มที่ 1
python3 scripts/lsp_client.py --complete prog.hs 1 4
python3 scripts/lsp_client.py --def prog.hs 2 10
python3 scripts/lsp_client.py --symbols prog.hs
python3 scripts/lsp_client.py --format prog.hs [--write]
```
