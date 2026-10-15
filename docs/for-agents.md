# for agents — เขียน `.holy` ให้เร็วและไม่พัง

กฎฉบับเต็มอยู่ที่ `../AGENTS.md` (อ่านก่อนเขียนโค้ด) หน้านี้คือ
ทางลัด + เครื่องมือที่ agent เรียกใช้ได้ทันที

## ขั้นตอนเขียนโปรแกรม (ไม่เดา)

```sh
python3 hs.py check prog.holy    # 1. syntax + scope เร็ว (ไม่รัน)
python3 hs.py run prog.holy      # 2. build ด้วย gcc แล้วรัน
python3 interp.py prog.holy     # 3. พฤติกรรมอ้างอิง (ช้ากว่า แต่คือความจริง)
python3 tests/test.py          # 4. เทสทั้งชุด
```

ทั้ง 4 คำสั่งรองรับ `--json` → error เป็น
`{"file":...,"line":...,"message":...}` บน stderr ให้แก้ตรงบรรทัด:

```sh
python3 hs.py --json check prog.holy
```

## เพิ่มเคสใหม่ในเทส

เขียน `tests/<name>.holy` + `tests/<name>.expected` (stdout ที่ถูกต้อง)
หรือ `tests/<name>.fail` (บรรทัด error ที่คาด) ถ้าเคสนั้นควรพัง
เพิ่ม `tests/<name>.args` / `.stdin` / `.env` ถ้าต้องการ แล้วรัน:

```sh
python3 tests/test.py          # interp (35)
python3 tests/test_native.py   # native + fmt + docs (38)
python3 tests/test_x64.py      # x64 subset (25)
python3 tests/test_xkernel.py  # QEMU boot จริง (58)
python3 tests/test_lsp.py      # LSP protocol (11)
```

`.holy` ที่มี `import` ถูกข้ามใน x64 ถ้าโมดูลอยู่นอก subset — เทสจะบอก

## เครื่องมือช่วยตัวเอง (LSP แบบคำสั่งเดียว)

```sh
python3 scripts/lsp_client.py --diag prog.holy          # error + line
python3 scripts/lsp_client.py --symbols prog.holy       # def/ตัวแปรทั้งไฟล์
python3 scripts/lsp_client.py --hover prog.holy 3 5     # builtin/keyword/ตัวแปร
python3 scripts/lsp_client.py --def prog.holy 2 10      # ไปที่จุดที่นิยาม
python3 scripts/lsp_client.py --complete prog.holy 1 4  # keyword+builtin+ชื่อในไฟล์
python3 scripts/lsp_client.py --refs prog.holy 2 10     # ทุกจุดที่เรียก (ข้ามไฟล์)
python3 scripts/lsp_client.py --sig prog.holy 4 9       # signature ของที่กำลังเรียก
python3 scripts/lsp_client.py --wsym prog.holy name    # ค้นชื่อทั้งโปรเจกต์
python3 scripts/lsp_client.py --format prog.holy --write  # เขียนกลับ canonical
```

(line/col เริ่มที่ 1 — human-friendly)

## ข้อมูลชิ้นเดียวกันสำหรับโปรแกรมอ่าน

```sh
python3 scripts/gen_api.py     # เขียน docs/api.json + docs/builtins.md ใหม่
python3 scripts/gen_errors.py  # เขียน docs/errors.md ใหม่ (ดึงจาก source)
```

`docs/api.json` = keywords + builtin (sig/desc/backend ที่รองรับ)
`docs/errors.md` = ข้อความ error ทุกข้อความในภาษา + ตาราง error ที่เจอบ่อย
`scripts/lang_data.py` = แหล่งกลางที่ LSP กับเทสใช้ร่วมกัน

## กับดักที่ทำให้เทสพังบ่อย

1. `//` เป็นคอมเมนต์เสมอ — หารไม่มี (ใช้ `/`)
2. `;` `{` `}` ไม่มีในภาษา
3. `for i in 0..5` ไม่มี — ใช้ `range(5)`
4. `print (1+2)*3` พัง — เขียน `print ((1+2)*3)`
5. ไม่รู้ว่า error แปลว่าอะไร → grep ใน `docs/errors.md` (มีครบทุกข้อความ)
6. error ทุกอันหน้าตาเป็น `error: <msg> at line N` (stderr, exit 1)
7. `print x, y` เว้นวรรค + newline ท้าย — ไม่ใช่ separator แบบ print ของ Python
8. เทสที่ต้องเขียนไฟล์/argv/stdin ต้องมี `.args`/`.stdin` ด้วย
   และอย่าใช้ path แบบ absolute

## เขียนโค้ดชิ้นไหนได้บ้าง

| งาน | ทำได้ที่ |
|---|---|
| สคริปต์ทั่วไป / stdlib ใหม่ (`std/*.holy`) | interp + native (ทุกฟีเจอร์) |
| ต้องรันโดยไม่มี gcc | x64 subset (`hs.py xbuild`) |
| kernel / OS | x64 subset + `unsafe:` + `xkernel` |
| ต่อ C / ภาษาอื่น | `extern:` (hosted เท่านั้น) |

ดูขอบเขตแบบละเอียดที่ `x64-subset.md` และ `../AGENTS.md`
