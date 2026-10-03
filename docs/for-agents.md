# for agents — เขียน `.hs` ให้เร็วและไม่พัง

กฎฉบับเต็มอยู่ที่ `../AGENTS.md` (อ่านก่อนเขียนโค้ด) หน้านี้คือ
ทางลัด + เครื่องมือที่ agent เรียกใช้ได้ทันที

## ขั้นตอนเขียนโปรแกรม (ไม่เดา)

```sh
python3 hs.py check prog.hs    # 1. syntax + scope เร็ว (ไม่รัน)
python3 hs.py run prog.hs      # 2. build ด้วย gcc แล้วรัน
python3 interp.py prog.hs     # 3. พฤติกรรมอ้างอิง (ช้ากว่า แต่คือความจริง)
python3 tests/test.py          # 4. เทสทั้งชุด
```

ทั้ง 4 คำสั่งรองรับ `--json` → error เป็น
`{"file":...,"line":...,"message":...}` บน stderr ให้แก้ตรงบรรทัด:

```sh
python3 hs.py --json check prog.hs
```

## เพิ่มเคสใหม่ในเทส

เขียน `tests/<name>.hs` + `tests/<name>.expected` (stdout ที่ถูกต้อง)
หรือ `tests/<name>.fail` (บรรทัด error ที่คาด) ถ้าเคสนั้นควรพัง
เพิ่ม `tests/<name>.args` / `.stdin` / `.env` ถ้าต้องการ แล้วรัน:

```sh
python3 tests/test.py          # interp (35)
python3 tests/test_native.py   # native + fmt + docs (38)
python3 tests/test_x64.py      # x64 subset (25)
python3 tests/test_xkernel.py  # QEMU boot จริง (58)
python3 tests/test_lsp.py      # LSP protocol (11)
```

`.hs` ที่มี `import` ถูกข้ามใน x64 ถ้าโมดูลอยู่นอก subset — เทสจะบอก

## เครื่องมือช่วยตัวเอง (LSP แบบคำสั่งเดียว)

```sh
python3 scripts/lsp_client.py --diag prog.hs          # error + line
python3 scripts/lsp_client.py --symbols prog.hs       # def/ตัวแปรทั้งไฟล์
python3 scripts/lsp_client.py --hover prog.hs 3 5     # builtin/keyword/ตัวแปร
python3 scripts/lsp_client.py --def prog.hs 2 10      # ไปที่จุดที่นิยาม
python3 scripts/lsp_client.py --complete prog.hs 1 4  # keyword+builtin+ชื่อในไฟล์
python3 scripts/lsp_client.py --format prog.hs -w    # เขียนกลับ canonical
```

(line/col เริ่มที่ 1 — human-friendly)

## ข้อมูลชิ้นเดียวกันสำหรับโปรแกรมอ่าน

```sh
python3 scripts/gen_api.py    # เขียน docs/api.json + docs/builtins.md ใหม่
```

`docs/api.json` = keywords + builtin (sig/desc/backend ที่รองรับ)
`scripts/lang_data.py` = แหล่งกลางที่ LSP กับเทสใช้ร่วมกัน

## กับดักที่ทำให้เทสพังบ่อย

1. `//` เป็นคอมเมนต์เสมอ — หารไม่มี (ใช้ `/`)
2. `;` `{` `}` ไม่มีในภาษา
3. `for i in 0..5` ไม่มี — ใช้ `range(5)`
4. `print (1+2)*3` พัง — เขียน `print ((1+2)*3)`
5. error ทุกอันหน้าตาเป็น `error: <msg> at line N` (stderr, exit 1)
6. `print x, y` เว้นวรรค + newline ท้าย — ไม่ใช่ separator แบบ print ของ Python
7. เทสที่ต้องเขียนไฟล์/argv/stdin ต้องมี `.args`/`.stdin` ด้วย
   และอย่าใช้ path แบบ absolute

## เขียนโค้ดชิ้นไหนได้บ้าง

| งาน | ทำได้ที่ |
|---|---|
| สคริปต์ทั่วไป / stdlib ใหม่ (`std/*.hs`) | interp + native (ทุกฟีเจอร์) |
| ต้องรันโดยไม่มี gcc | x64 subset (`hs.py xbuild`) |
| kernel / OS | x64 subset + `unsafe:` + `xkernel` |
| ต่อ C / ภาษาอื่น | `extern:` (hosted เท่านั้น) |

ดูขอบเขตแบบละเอียดที่ `x64-subset.md` และ `../AGENTS.md`
