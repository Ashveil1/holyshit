# holyshit LSP (`lsp.py` + `hs.py lsp`)

language server ผ่าน stdio (JSON-RPC, ไม่ต้องลง lib เพิ่ม).
รันด้วย `python3 hs.py lsp` หรือ `python3 lsp.py` ตรง ๆ

## ความสามารถ

| ฟีเจอร์ | วิธี |
|---|---|
| diagnostics | parse + scope check ทุกครั้งที่เปิด/แก้ไฟล์/บันทึก (line ตรง `hs.py check`) |
| hover | builtin (signature + backend), keyword, def/param/ตัวแปร, `mod.attr` (บอกไฟล์ที่นิยาม) |
| completion | keyword + builtin + ชื่อในไฟล์; หลัง `mod.` เสนอเฉพาะชื่อระดับบนของโมดูล |
| goto definition | ในไฟล์ + ข้ามไฟล์ (`mod.attr`, `import mod`, submodule ที่ re-export) |
| references | ทุกจุดที่เรียก ข้ามไฟล์ในโฟลเดอร์เดียวกัน + `HSPATH` (มีตัวประกาศด้วย) |
| document highlight | ทุกจุดของชื่อในบรรทัดนั้น + บรรทัดที่ประกาศ |
| signature help | ทั้ง `def` ของผู้ใช้และ builtin (`activeParameter` เดินตามจุลภาค) |
| document symbols | `def` / ตัวแปร / import ระดับไฟล์ |
| workspace symbols | ค้นชื่อข้ามทั้งโปรเจกต์ |
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
python3 scripts/lsp_client.py --diag prog.holy
python3 scripts/lsp_client.py --hover prog.holy 3 5     # line/col เริ่มที่ 1
python3 scripts/lsp_client.py --complete prog.holy 1 4
python3 scripts/lsp_client.py --def prog.holy 2 10
python3 scripts/lsp_client.py --refs prog.holy 2 10     # references ทั้งโปรเจกต์
python3 scripts/lsp_client.py --highlight prog.holy 2 10
python3 scripts/lsp_client.py --sig prog.holy 4 9       # signature help
python3 scripts/lsp_client.py --wsym prog.holy double   # workspace symbols
python3 scripts/lsp_client.py --symbols prog.holy
python3 scripts/lsp_client.py --format prog.holy [--write]
```

ข้อจำกัดที่รู้แล้ว: references/workspace symbols แวนกวางไฟล์ `.holy` ในโฟลเดอร์
ของไฟล์ที่เปิด (ข้าม `.git`, `legacy`, `__pycache__`) บวก `HSPATH` — จึงยังไม่ใช่
index ทั้ง workspace แบบเต็ม แต่พอสำหรับโปรเจกต์ที่ `.holy` อยู่รวมกัน
