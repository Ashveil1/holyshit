# holyshit — วิสัยทัศน์ (VISION)

> เขียนเมื่อ 2026-10-12 ที่สถานะ **v0.6.30** จากเป้าหมายที่เจ้าของโปรเจกต์ (Ash) บอกไว้เอง
> Current evidence checkpoint updated 2026-10-14; original goals retained (see `docs/bench.md`).
> ไฟล์นี้คือ "เป้าหมายที่เปิดดูได้ทุกเมื่อ" — แผนลงมือทำอยู่ที่ [`ROADMAP.md`](ROADMAP.md)
>
> ป้ายในไฟล์นี้: **[เอกสาร]** = มีเขียนไว้ใน SPEC/docs/commit จริง ·
> **[วัดจริง]** = มีตัวเลขหรือเทสในรีโป · **[อนุมาน]** = ผู้เขียนเอกสารนี้สรุปเอง ยังไม่มีไฟล์ยืนยัน ·
> **[ยังไม่มี]** = ไม่พบในรีโป

## เป้าหมาย 7 ข้อ (คำของเจ้าของ สรุปสั้น)

holyshit (hs) จะเป็นภาษาที่:

1. **เร็วกว่า Python**
2. **ไม่ต้องคอมไพล์เอง — รันแบบ JIT** (เขียนแล้วรันทันที แต่เร็วระดับ native)
3. **เขียนง่ายกว่า Python**
4. **สร้าง OS ได้ด้วยตัวมันเอง** แทบไม่ต้องใช้ภาษาอื่น
5. **พึ่งตัวเองสมบูรณ์** (self-reliant: ไม่ต้องมี gcc/as/ld/libc, สุดท้าย compiler เขียนด้วย hs เอง)
6. **เข้ากันได้กับภาษาอื่น** — เรียกไลบรารีภาษาอื่นได้ (FFI)
7. **ออกแบบให้ AI เป็นคนเขียนเป็นหลัก** — ให้เป็นภาษาที่ AI เขียนได้ดีที่สุด

**ตัดออกจากเป้าหมาย (เจ้าของสั่ง 2026-10-12):** การใช้ไลบรารี Python ได้ครบสมบูรณ์ — ไม่ต้องทำ
(FFI ข้อ 6 ยังอยู่ แต่ไม่ต้องรองรับ CPython C-API / numpy ฯลฯ)

## สถานะต่อเป้าหมายแต่ละข้อ (ที่ v0.6.30)

### Current evidence checkpoint: 2026-10-14

This checkpoint replaces the original v0.6.30 status assessment. The seven
owner goals above are unchanged. Passing tests establish the stated scope,
not completion of a whole goal.

| Goal | What is demonstrated | What remains |
|---|---|---|
| Faster than Python | `bench/run.py` checks equal outputs against CPython. Local int/recursion cases are about 5-6x faster; alloc/dict/string results vary. Hash-indexed dicts and conservative mark-sweep GC replaced the original bottlenecks. | Larger workloads, lower live-heap overhead, repeatable results on other machines. No universal speed claim. |
| No explicit compile / JIT | Default `hs run` builds and runs x64 with caching/fallback. `scripts/run-native.sh` compiles and runs through the native hs seed without Python/gcc. | Neither path is a JIT. In-memory compilation/execution, first-call compilation and tiering are not implemented. |
| Easier than Python | Methods on builtins, lambda, classes/inheritance, f-strings, comprehensions, default arguments, prelude helpers, formatter, errors, REPL and LSP exist. | No human usability or model comparison establishes that hs is easier. Syntax is not Python-compatible. |
| Write an OS in hs | Public xkernel uses IR. Full CI runs the unchanged QEMU corpus, 291/291, on IR and retained AST paths. The hs IR kernel compiler produces reference-identical complete ELFs. `scripts/build-kernel-native.sh` builds without Python/gcc/as/ld. | Real hardware, network stack, disk filesystem, SMP/USB/graphics and a standalone boot/distribution story are not established by these gates. |
| Self-reliance | Parser, normalization, IR builder/optimizer/verifier, x64 runtime/code generator, assembler and ELF linker have hs implementations. An audited Linux x86-64 seed compiles itself twice with seed == stage2 == stage3. The hosted/native kernel routes need no Python execution. | The repository still uses Python for reference semantics, tests, regeneration, tooling and an independent source audit. The seed needs repository sources/runtime data; it is not a portable standalone distribution. |
| Interoperation | C ABI I64/U64/F64/Str/Ptr/U0 works in interp, native and x64. A struct-by-pointer regression uses gmtime_r and explicit field access. | Struct-by-value, callbacks and variadic calls are not supported. No broad language-library compatibility claim. |
| AI-first | Structured errors, formatter, test runner, explanations, LSP, API docs and 39 evaluation tasks/checker exist. | No model run or pass@1 result. A task count is not an AI-quality measurement. |

Overall progress is approximately **70%**, an engineering estimate against
these seven goals, not a percentage calculated from tests or a promise that
80% is reached. The largest unfinished areas are real JIT, wider FFI,
GC/performance work and measured AI/usability evaluations.

Evidence and commands: [`ROADMAP.md`](ROADMAP.md), [`bench.md`](bench.md),
[`../bootstrap/README.md`](../bootstrap/README.md),
`tests/test_native_compiler.py`, `tests/test_hosted_seed.py`,
`tests/test_native_kernel_ir.py`, `tests/test_native_kernel_command.py`,
`tests/test_xkernel.py` and `tests/test_kernel_ir.py`.

## ความขัดแย้งในตัวเป้าหมาย (ต้องตัดสินใจ — ดู ROADMAP "ความเสี่ยง")

- **JIT + ไม่ต้องคอมไพล์ vs พึ่งตัวเองสมบูรณ์:** JIT ต้องมีตัวสร้างโค้ดเครื่องที่รันใน process เดียวกัน
  (ทำได้ เพราะมี encoder `x64.py` อยู่แล้ว) แต่ถ้าเขียนด้วย Python ก็ยังพึ่ง Python อยู่ — ต้อง self-host ก่อนถึงจะ "พึ่งตัวเอง" จริง
- **เร็วกว่า Python vs ข้อความ error ละเอียด + tagged value:** SPEC §13 วัดแล้วว่า error check ทำให้ช้าลง
- **ง่ายกว่า Python (dynamic) vs เร็ว (static):** dynamic ทั้งหมดทำให้ JIT ต้องมี type feedback/specialization
- **ใช้ทุกอย่างได้เหมือนทุกภาษา vs ตัดไลบรารี Python:** เจ้าของตัดข้อหลังออกแล้ว ใช้ FFI แทน
