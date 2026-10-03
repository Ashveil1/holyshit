# holyshit docs — เริ่มตรงนี้

ภาษา dynamic เขียนง่ายแบบ Python, มี 4 ปลายทางรัน (ดูตารางใน `builtins.md`
ว่าของชิ้นไหนรันที่ไหนได้บ้าง)

| อยาก... | อ่าน |
|---|---|
| **cheatsheet หน้าเดียวจบ** | `cheatsheet.md` |
| เขียนโปรแกรมแรกใน 10 นาที | `tutorial.md` |
| ดูตัวอย่างที่รันได้จริง | `../examples/` |
| หา builtin/keyword (คน) | `builtins.md` |
| เขียน `std.*` เอง / ใช้ std | `stdlib.md` |
| รันแบบไม่ใช้ gcc / ลง bare metal | `x64-subset.md`, `kernel.md` |
| ต่อ editor / ให้ AI เรียกใช้ภาษา | `lsp.md`, `for-agents.md` |
| ให้โปรแกรมช่วยอ่าน (JSON) | `api.json` |
| เหตุผลออกแบบ + ประวัติเฟส | `../SPEC-v1.md` |
| กฎฉบับกระชับที่สุด | `../AGENTS.md` |

รันเร็วสุด:

```sh
python3 interp.py prog.hs     # tree-walk, พฤติกรรมอ้างอิง
python3 hs.py check prog.hs   # ตรวจ syntax/scope
python3 hs.py build prog.hs   # native binary ผ่าน gcc
python3 hs.py xbuild prog.hs  # machine code ตรง ไม่ใช้ gcc
python3 hs.py xkernel prog.hs -o k.elf  # kernel บูต QEMU ได้
python3 hs.py lsp             # language server (stdio)
```
