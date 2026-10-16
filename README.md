# holyshit (hs) — v0.6.30

ภาษา dynamic เขียนง่ายแบบ Python, รันได้ 4 โหมด, ต่อ C ได้, ลง bare metal ได้,
มี language server ให้ editor และ AI agent

## Install and run (Linux x86-64)

The normal run/build route is the audited native bundle. From this checkout,
install into a **new directory** whose parent already exists:

```sh
sh scripts/install-native.sh "$HOME/holyshit-native"
"$HOME/holyshit-native/bin/hs" run examples/hello.holy
"$HOME/holyshit-native/bin/hs" build examples/hello.holy /tmp/hello-hs
/tmp/hello-hs
```

No Python or gcc is needed to install or use this route. It needs Linux
x86-64, `/bin/sh`, standard shell/checksum utilities and host libc/shared
libraries for FFI. Installation builds the eager driver once and can take
time. Move the whole installed directory together; no checkout is needed
after installation. The installer does not edit PATH/shell profiles, use sudo
or overwrite an existing directory. Use a new directory for each update;
keep the old one until the new version is checked. Removing an install means
removing only its chosen directory, not any source checkout.

The native launcher currently provides only `run SOURCE [args...]` and
`build SOURCE OUTPUT`. It reports unsupported hosted-subset programs rather
than silently falling back. It does not provide the Python CLI's check, fmt,
test, REPL, LSP or kernel commands. `run` compiles eagerly in memory, not on
first call or in tiers. The installed prebuilt driver is not rebuilt per run.
See [native install details](docs/native-install.md).

## Development and reference tools (Python)

These remain available for independent semantic checks, diagnostics, editor
support and development. They are not required by the installed run/build
route. Their backend behavior differs from the native launcher:

```sh
python3 interp.py prog.holy [args...]   # รันทันที (tree-walk)
python3 hs.py check prog.holy           # ตรวจ syntax/scope อย่างเดียว
python3 hs.py build prog.holy [-o prog] # เป็น native binary (gcc + Boehm GC)
python3 hs.py run prog.holy [args...]   # build ลง temp แล้วรันทันที (ค่าเริ่มต้น: x64 ไม่ใช้ gcc, fallback เอง)
HS_BACKEND=auto|x64|native|interp     # เลือก backend ของ run (หรือ run prog.holy --backend X)
python3 hs.py fmt prog.holy [-w|--check] # จัดรูป canonical (2-space, ตัดคอมเมนต์)
python3 hs.py test file_or_dir...      # รันทุก `def test_*()` (assert = เทส); --json สำหรับเอเจนต์, exit 1 ถ้ามีที่ fail
python3 hs.py repl                       # REPL: state ค้างข้ามบรรทัด, นิพจน์เปล่าพิมพ์ค่า, error ไม่ทำให้หลุด
python3 hs.py run selfhost/cc.holy prog.holy out   # คอมไพเลอร์ที่เขียนด้วย hs เอง: Int/def/while/print → ELF x86-64 (ดู tests/test_cc.py)
python3 hs.py xbuild prog.holy [-o prog] # machine code ตรง ไม่ใช้ gcc (subset)
python3 hs.py xkernel prog.holy -o k.elf # kernel freestanding ไม่ใช้ gcc/as/ld
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
`examples/hello.holy` → `fib.holy` → `closure.holy` → `ffi.holy`

- dynamic types: Int Float Str Bool Null List Dict Func (+ first-class)
- `def if/while/for try/except import` — syntax indent แบบ Python
  (`import std.str` แบบ dotted ได้, std อยู่ใน `std/`)
- `unsafe:` — I64/U64/Ptr + `asm` ตรง (static subset ในภาษาเดียวกัน)
- `extern [from ...]:` — เรียก C/.so/ภาษาไหนก็ได้ผ่าน C ABI
- closure (copy semantics), JSON, socket/HTTP client, argv/env/system
- มี x64 subset ที่รันได้โดยไม่ต้องมี gcc เลย (รวมถึง kernel) — มีครบ
  Int/Float/Str/List/Dict/Bool/Null, `- * / %` เทียบ float และ
  `print`/`float()` แบบ shortest round-trip ตรงกับ Python โดยไม่ใช้ libc,
  `json_parse`/`json_str` (คอมไพล์จาก `runtime/json.holy` เข้าไปใน image)

## เทส

```sh
python3 tests/run_all.py         # ทุกชุด (ข้าม kernel ด้วย --quick)
python3 tests/test.py          # interpreter (49 ชุด)
python3 tests/test_native.py   # native binary (49 ชุด, ผลต้องตรง interp)
python3 tests/test_fmt.py      # formatter (canonical+idempotent+exec+ทั้ง repo)
python3 tests/test_x64.py      # backend x86-64 ตรง (x64/ + ทั้งคอร์ปัส interp, 98, static ELF)
python3 tests/test_ir.py       # IR กลาง: build/verify/exec ตรง interp ทุกไบต์ (139)
python3 tests/test_irx64.py    # IR->x64 เทียบกับ path เก่า (42, ELF ชน ELF)
python3 tests/test_xkernel.py  # kernel freestanding บูตจริงบน QEMU (291 เคส)
python3 tests/test_examples.py # ตัวอย่างทุกไฟล์ยังรันได้จริง (17)
python3 tests/test_lsp.py      # language server ผ่าน stdio (25 เคส)
python3 tests/test_docs.py     # เอกสาร: โค้ดใน tutorial รันจริง + ลิงก์ + api.json (41)
```

กติกาเทส: `tests/<name>.holy` + `.expected` (stdout), `.stdin` (input),
`.args` (argv ทีละบรรทัด), `.env` (KEY=VAL ต่อบรรทัด), `.fail` (error ที่คาด,
เทียบ stderr), `mod_*` = helper (ไม่รันตรง), `.nativeonly` = ข้ามฝั่ง interp

## editor

language server เป็น stdio ล้วน ไม่ต้องลงอะไรเพิ่ม — ชี้ editor ไปที่
`python3 <repo>/lsp.py` ได้เลย (VS Code / Neovim / Helix / Zed มีตัวอย่างใน
`editors/`)

```sh
python3 hs.py lsp                                  # server
python3 scripts/lsp_client.py --diag prog.holy       # คำสั่งเดียวจบ (สำหรับ agent)
```

## สำหรับ AI agent

อ่าน `AGENTS.md` ก่อนเขียน `.holy` เสมอ — reference กระชับครบกฎทั้งหมด
รวม gotchas และ fix loop (`check` → `interp` → `build`, error มี `--json`)
สั้นกว่านั้นดู `docs/for-agents.md`

## License

Apache License 2.0 - see `LICENSE`. Copyright 2026 Ashveil1.
