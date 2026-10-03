# holyshit VS Code extension

ไม่ต้อง `npm install` — `client.js` spawn `python3 ../../lsp.py` เอง
(ถ้ามี `vscode-languageclient` ในเครื่องก็จะใช้ตัวนั้น)

## ใช้

1. เปิด `editors/vscode/` ใน VS Code
2. `npm run dev:install` (ครั้งเดียว — ลง `holyshit` extension) หรือกด F5
   เพื่อเปิด Extension Development Host
3. เปิดไฟล์ `.hs` → diagnostics/hover/completion/goto ใช้ได้ทันที

ตั้ง python อื่นได้ด้วย env:

```sh
HS_PYTHON=/usr/bin/python3.12 code editors/vscode
```

## ไฟล์

- `package.json` — contributes language `holyshit` + คำสั่ง restart/check
- `language-configuration.json` — comment `#`, indent ตาม `:`, bracket
- `client.js` — จุดเชื่อม LSP (stdlib + `vscode-languageclient` ถ้ามี)

## ถ้าอยากใช้กับโปรเจกต์อื่น

เพิ่มการเชื่อม `.hs` เข้ากับ LSP ตรง ๆ ใน `settings.json` ของโปรเจกต์:

```json
{
  "files.associations": { "*.hs": "holyshit" },
  "holyshit.serverPath": "/path/to/holyshit/lsp.py"
}
```
