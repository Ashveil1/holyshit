# bench — hs เทียบ CPython

รัน: `python3 bench/run.py [ชื่อ ...] [--timeout วินาที]`
แต่ละเคสมีคู่ `bench/<name>.holy` + `bench/<name>.py` ที่พิมพ์ผลเหมือนกัน (สคริปต์เช็คให้)
เทียบ `hs.py xbuild` (ELF ตรง ไม่ใช้ gcc) กับ CPython; CI รันทุกคืนแล้วเก็บผลเป็น artifact

## Baseline ที่ v0.6.30 (วัดเมื่อ 2026-10-12)

เครื่อง: sandbox 2 core, CPython 3.10.12 (ตัวเลขสัมบูรณ์ต่างกันตามเครื่อง ดูอัตราส่วนเป็นหลัก)

| เคส | CPython | hs xbuild | เร็วกว่า | MB py | MB hs | หมายเหตุ |
|---|---|---|---|---|---|---|
| fib(32) | 0.35 s | 0.07 s | 5.2x | 9 | 9 | เรียกฟังก์ชันซ้ำ |
| loop 20M (บวก/mod) | 1.38 s | 0.22 s | 6.4x | 9 | 9 | int ล้วน |
| strings (3M append+join+split) | 0.74 s | 0.36 s | 2.1x | 444 | 406 | |
| alloc (5M `"abc"+str(i)`) | 1.05 s | 0.60 s | 1.7x | 9 | **687** | ไม่มี free ใน x64 — หน่วยความจำโตไม่หยุด |
| dict (200k insert + วน) | 0.10 s | **>20 s (timeout)** | **ช้ากว่า ~1000x** | - | - | ค้น key แบบ linear scan (`emit_dict_helpers`) |

ที่วัดไว้ครั้งแรก (ไม่อยู่ใน `bench/`): dict 200k insert = 117.5 s เทียบ CPython 0.096 s

## ข้อสรุป

- งาน int/เรียกฟังก์ชัน เร็วกว่า CPython ~5-6x แล้ว
- สองจุดที่ต้องแก้ก่อนจะอ้างว่า "เร็วกว่า Python": dict แบบ hash จริง และตัวจัดสรรหน่วยความจำที่ free ได้ (ดู `ROADMAP.md` เฟส 1)
- ตัวเลข interp.py (tree-walk): fib(22) 436 ms เทียบ CPython 15 ms — ใช้เป็นข้อกำหนดพฤติกรรม ไม่ใช่ทางที่เร็ว

## หลังเพิ่ม GC (P1, branch p1-gc)

conservative mark-sweep บน IR→x64 (`gcrt.py`): เก็บเฉพาะที่ safe point (ทางเข้าฟังก์ชัน / หัวลูป)
roots = stack + data segment + บล็อก `unsafe alloc` (pinned). `x64`/kernel runtime ไม่เปลี่ยน.

| bench | ก่อน | หลัง |
|---|---|---|
| alloc (5M strings) | 0.60 s, 687 MB | 0.45 s, 9-16 MB |
| fib / loop / dict | - | ไม่ต่างจากเดิมอย่างมีนัย |
| strings (3M live strs) | 0.32 s | 0.66 s (header 16B + bitmap + GC scan) |

ทดสอบ: `tests/x64/gc_stress.holy` (diff กับ interp), `gc bound` ใน test_x64 (alloc bench < 50 MB),
และรัน suites ทั้งหมดด้วย GC ทุก 4 KB ผ่าน (ใช้ตอนพัฒนา).

## Compact immutable strings (2026-10-14)

Removing unnecessary extra slack from x_str_at/x_str_cat reduces the
3-million-string benchmark's local peak RSS from 469 MB to 377 MB.
Nine alternating baseline/candidate runs on the same host measured
medians 0.580149s and 0.520208s (about 10% lower runtime). All outputs
match. This is a local result, not a cross-machine speed guarantee.
The GC arena-cache experiment was discarded after it did not improve
alternating-run medians. Allocation churn remains bounded by GC.
