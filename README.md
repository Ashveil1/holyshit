# holyshit (hs) — v0.6.22

ภาษา dynamic เขียนง่ายแบบ Python, รันได้ 4 โหมด, ต่อ C ได้, ลง bare metal ได้,
มี language server ให้ editor และ AI agent

```sh
python3 interp.py prog.hs [args...]   # รันทันที (tree-walk)
python3 hs.py check prog.hs           # ตรวจ syntax/scope อย่างเดียว
python3 hs.py build prog.hs [-o prog] # เป็น native binary (gcc + Boehm GC)
python3 hs.py run prog.hs [args...]   # build ลง temp แล้วรันทันที
python3 hs.py fmt prog.hs [-w|--check] # จัดรูป canonical (2-space, ตัดคอมเมนต์)
python3 hs.py xbuild prog.hs [-o prog] # machine code ตรง ไม่ใช้ gcc (subset)
python3 hs.py xkernel prog.hs -o k.elf # kernel freestanding ไม่ใช้ gcc/as/ld
python3 hs.py lsp                     # language server (stdio, ไม่มี dependency)
python3 hs.py --version
```

เริ่มอ่านที่ **[`docs/index.md`](docs/index.md)** — cheatsheet, tutorial, ตัวอย่าง
ที่รันได้จริง, stdlib, x64 subset, kernel, LSP, คู่มือสำหรับ AI agent

## ตัวอย่าง 30 วินาที

```
def fib(n):
  if n < 2:
    return n
  return fib(n - 1) + fib(n - 2)

print fib(10)

extern from "m":
  F64 sin(F64 x)

print sin(0.0)
```

## โครงโปรเจกต์

| ส่วน | ไฟล์ |
|---|---|
| เอกสารทั้งหมด (เริ่มตรงนี้) | `docs/index.md` |
| กฎสำหรับ AI agent | `AGENTS.md` |
| สเปกภาษา + เหตุผลออกแบบ | `SPEC-v1.md` |
| มีส่วนร่วม | `CONTRIBUTING.md` |
| interpreter (พฤติกรรมอ้างอิง) | `interp.py` |
| native backend (AST→C→gcc) + CLI | `hs.py` + `native/rt.{h,c}` |
| x86-64 backend ตรง (subset, ไม่ใช้ gcc, ค่าแบบ tagged) | `x64.py` + `x64gen.py` |
| kernel runtime (freestanding) | `kernel/` |
| ไลบรารีมาตรฐาน (เขียนด้วย hs) | `std/` |
| language server (diagnostics/hover/goto/format) | `lsp.py` + `editors/` |
| ข้อมูลภาษาแบบเครื่องอ่านได้ | `docs/api.json`, `docs/errors.md`, `scripts/lang_data.py` |
| ตัวอย่างตามหัวข้อ | `examples/` |
| เทส | `tests/` |
| ของเก่า v0.3 (WASM) | `legacy/` |

## หัวข้อหลักในภาษา

ดู `SPEC-v1.md` ฉบับเต็ม — ไล่จากง่ายไปยาก:
`examples/hello.hs` → `fib.hs` → `closure.hs` → `ffi.hs`

- dynamic types: Int Float Str Bool Null List Dict Func (+ first-class)
- `def if/while/for try/except import` — syntax indent แบบ Python
  (`import std.str` แบบ dotted ได้, std อยู่ใน `std/`)
- `unsafe:` — I64/U64/Ptr + `asm` ตรง (static subset ในภาษาเดียวกัน)
- `extern [from ...]:` — เรียก C/.so/ภาษาไหนก็ได้ผ่าน C ABI
- closure (copy semantics), JSON, socket/HTTP client, argv/env/system
- มี x64 subset ที่รันได้โดยไม่ต้องมี gcc เลย (รวมถึง kernel) — มีครบ
  Int/Float/Str/List/Dict/Bool/Null, `- * / %` เทียบ float และ
  `print`/`float()` แบบ shortest round-trip ตรงกับ Python โดยไม่ใช้ libc,
  `json_parse`/`json_str` (คอมไพล์จาก `runtime/json.hs` เข้าไปใน image)

## เทส

```sh
python3 tests/run_all.py         # ทุกชุด (ข้าม kernel ด้วย --quick)
python3 tests/test.py          # interpreter (42 ชุด)
python3 tests/test_native.py   # native binary (43 ชุด, ผลต้องตรง interp)
python3 tests/test_fmt.py      # formatter (canonical+idempotent+exec+ทั้ง repo)
python3 tests/test_x64.py      # backend x86-64 ตรง (52 ชุด, static ELF, ไม่ใช้ gcc)
python3 tests/test_ir.py       # IR กลาง: build/verify/exec ตรง interp ทุกไบต์ (47)
python3 tests/test_xkernel.py  # kernel freestanding บูตจริงบน QEMU (291 เคส)
python3 tests/test_examples.py # ตัวอย่างทุกไฟล์ยังรันได้จริง (17)
python3 tests/test_lsp.py      # language server ผ่าน stdio (25 เคส)
python3 tests/test_docs.py     # เอกสาร: โค้ดใน tutorial รันจริง + ลิงก์ + api.json (38)
```

กติกาเทส: `tests/<name>.hs` + `.expected` (stdout), `.stdin` (input),
`.args` (argv ทีละบรรทัด), `.env` (KEY=VAL ต่อบรรทัด), `.fail` (error ที่คาด,
เทียบ stderr), `mod_*` = helper (ไม่รันตรง), `.nativeonly` = ข้ามฝั่ง interp

## editor

language server เป็น stdio ล้วน ไม่ต้องลงอะไรเพิ่ม — ชี้ editor ไปที่
`python3 <repo>/lsp.py` ได้เลย (VS Code / Neovim / Helix / Zed มีตัวอย่างใน
`editors/`)

```sh
python3 hs.py lsp                                  # server
python3 scripts/lsp_client.py --diag prog.hs       # คำสั่งเดียวจบ (สำหรับ agent)
```

## สำหรับ AI agent

อ่าน `AGENTS.md` ก่อนเขียน `.hs` เสมอ — reference กระชับครบกฎทั้งหมด
รวม gotchas และ fix loop (`check` → `interp` → `build`, error มี `--json`)
สั้นกว่านั้นดู `docs/for-agents.md`
