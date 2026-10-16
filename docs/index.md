# holyshit docs — เริ่มตรงนี้

ภาษา dynamic เขียนง่ายแบบ Python, มี 4 ปลายทางรัน (ดูตารางใน `builtins.md`
ว่าของชิ้นไหนรันที่ไหนได้บ้าง) เขียนเอกสารเองให้คนอ่าน/ให้ AI อ่าน/ให้เครื่องอ่าน —
และทุกอย่างที่เขียนไว้ถูกเทสตรวจว่าจริง

| อยาก... | อ่าน |
|---|---|
| ติดตั้งและรัน/build แบบ native (Linux x86-64) | [native-install.md](native-install.md) |
| **cheatsheet หน้าเดียวจบ** | `cheatsheet.md` |
| เขียนโปรแกรมแรกใน 10 นาที | `tutorial.md` |
| ดูตัวอย่างที่รันได้จริง | `../examples/` |
| หา builtin/keyword (คน) | `builtins.md` |
| หาว่า error แปลว่าอะไร | `errors.md` |
| เขียน `std.*` เอง / ใช้ std | `stdlib.md` |
| รันแบบไม่ใช้ gcc / ลง bare metal | `x64-subset.md`, `kernel.md` |
| ต่อ editor / ให้ AI เรียกใช้ภาษา | `lsp.md`, `for-agents.md` |
| ให้โปรแกรมช่วยอ่าน (JSON) | `api.json` |
| เหตุผลออกแบบ + ประวัติเฟส | `../SPEC-v1.md` |
| กฎฉบับกระชับที่สุด | `../AGENTS.md` |
| อยากช่วยเพิ่ม/แก้ภาษา | `../CONTRIBUTING.md` |

## Normal install/run/build (Linux x86-64)

```sh
sh scripts/install-native.sh "$HOME/holyshit-native"
"$HOME/holyshit-native/bin/hs" run examples/hello.holy
"$HOME/holyshit-native/bin/hs" build examples/hello.holy /tmp/hello-hs
```

Use a new directory with an existing parent. No Python/gcc is needed for
this route; shell/checksum utilities and host libc/shared libraries are
required. The installed launcher supports run/build of the hosted subset,
not all development commands or the entire language. See
[native install](native-install.md) for relocation, updates and limits.

## Development/reference tools (Python)


```sh
python3 interp.py prog.holy     # tree-walk, พฤติกรรมอ้างอิง
python3 hs.py check prog.holy   # ตรวจ syntax/scope
python3 hs.py build prog.holy   # native binary ผ่าน gcc
python3 hs.py xbuild prog.holy  # machine code ตรง ไม่ใช้ gcc
python3 hs.py xkernel prog.holy -o k.elf  # kernel บูต QEMU ได้
python3 hs.py lsp             # language server (stdio)
```
