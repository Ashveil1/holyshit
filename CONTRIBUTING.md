# contributing to holyshit

ภาษาเล็ก ๆ ที่เขียน/ทดสอบด้วย Python ล้วน (ไม่มี dependency) — เข้ามาช่วยได้ทั้งคน
และ AI agent

## เริ่มที่ไหน

| อยากทำ | ไฟล์ |
|---|---|
| เขียนภาษา/เอกสารให้คนอ่าน | `docs/index.md` → `docs/for-agents.md` |
| แก้ semantics | `interp.py` (อ้างอิงความจริง) แล้วให้ backend ตามให้ตรง |
| แก้ native backend (gcc) | `hs.py` + `native/rt.{h,c}` |
| แก้ x86-64 backend | `x64.py` (assembler) + `x64gen.py` (codegen + runtime) |
| แก้ formatter | `fmt.py` |
| แก้ LSP | `lsp.py` |
| แก้เครื่องมือ/เอกสารที่ generate | `scripts/lang_data.py`, `scripts/gen_*.py` |

## setup

```sh
python3 --version          # 3.8+ ไม่ต้อง pip install อะไรเลย
python3 hs.py check prog.hs
python3 tests/run_all.py   # --quick ข้ายส่วนที่ต้องใช้ qemu
```

เทสส่วน kernel ต้องมี `qemu-system-x86_64`; ถ้าไม่มีจะขึ้น `skip`

## กติกาเทส (สำคัญ)

1. ทุก `.hs` ต้องมี `.expected` (stdout) หรือ `.fail` (บรรทัด error ที่คาด)
2. `interp.py` คือความจริง — ถ้า native/x64 ต่างจาก interp **ตัวที่ต่างผิด**
3. เพิ่มเทสแล้วรัน `tests/test.py` + `tests/test_native.py` (+ `test_x64.py`
   ถ้าเป็นโค้ดที่อยู่ใน subset) — ห้ามลดจำนวนเทสเดิม
4. แตะ builtin/error/doc -> รัน `scripts/gen_api.py` / `scripts/gen_errors.py`
   แล้ว `tests/test_docs.py` (มันจะจับ drift ให้เอง)
5. แก้ `.hs` ภายนอก -> `python3 hs.py fmt <file> -w` ก่อน commit
   (`--check` ไม่นับคอมเมนต์/บรรทัดว่าง เทสตรวจว่าทั้ง repo canonical แล้ว)
6. โค้ดใน `docs/*.md` ที่อยู่ในบล็อก ```hs **ถูกรันจริง** โดยเทส ห้ามเขียนตัวอย่างที่รันไม่ผ่าน

## style

- Python: 4 spaces, ชื่อฟังก์ชัน/ตัวแปร snake_case, ไม่มี type hint ที่ไม่จำเป็น
- ใช้ f-string ได้ แต่ error message ที่ผู้ใช้เห็นต้องเป็นรูปแบบเดียวกันทั้ง backend
- เอกสารไทย + อังกฤษใช้ได้ทั้งคู่ แต่ให้ยึดภาษาไทยในบล็อกอธิบาย (ตามที่มีอยู่แล้ว)
- commit เขียนไทยได้ แต่บอกว่า "แก้อะไร / ทำไม / กระทบอะไร"

## commit ดี ๆ (ตัวอย่างจริงจากประวัติ)

```
fix: x64/kernel ข้าม finally เมื่อ except handler raise

แก้ใน x64gen.ex_try: คุม handler ด้วย hs_try_push0 อีกชั้น — error ใน handler
จะกระโดดมาที่ finally ก่อน แล้ว hs_reraise ต่อไปข้างนอก

เทส: tests/x64/try.hs, kernel/ktry.hs
```

## เพิ่ม builtin ใหม่

1. เพิ่มใน `interp.py` (`BUILTINS` + ฟังก์ชัน `b_*`)
2. ถ้าเป็น hosted-only ให้เพิ่มใน `hs.py` (BUILTINS + `native/rt.c`)
3. ถ้าทำบน x64 ได้ ให้เพิ่มใน `x64gen.py` + `native/rt.c` (ถ้า hosted)
4. อัปเดต `scripts/lang_data.py` (sig/desc/backend) — `tests/test_docs.py`
   จะฟันว่าครบและตรงกับ `interp.BUILTINS`
5. รัน `scripts/gen_api.py` + `scripts/test*.py`

## AI agent

อ่าน `AGENTS.md` ก่อนเสมอ แล้วใช้ `scripts/lsp_client.py` แทนการเดา:
`--diag` บอกบรรทัด, `--refs` บอกทุกจุดที่เรียก, `--def` พาไปจุดที่นิยาม
`AGENTS.md` ต้องสั้นและถูก — ถ้ากฎยาวเกินไปให้ย้ายไป `docs/`
