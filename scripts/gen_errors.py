#!/usr/bin/env python3
"""Generate docs/errors.md from the error messages in the sources.

    python3 scripts/gen_errors.py

Every `HSErr(...)` message in interp.py (hosted + parse), hs.py (gcc backend),
x64gen.py (x86-64 subset) and fmt.py becomes a row. tests/test_docs.py
regenerates and diffs, so the catalog cannot rot silently.
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# file -> (section title, note)
SOURCES = [
    ("interp.py", "interp.py — ตัวตีความ + parse (ทุก error ของภาษา)"),
    ("hs.py", "hs.py — native backend ผ่าน gcc"),
    ("x64gen.py", "x64gen.py — backend x86-64 ตรง (xbuild/xkernel)"),
    ("fmt.py", "fmt.py — formatter"),
    ("ir.py", "ir.py — IR กลาง (build/verify/exec)"),
    ("irx64.py", "irx64.py — IR ลง x86-64"),
]

# lines that are internal plumbing rather than user-facing advice
SKIP = re.compile(r"^(internal|unreachable)", re.I)


def messages(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "HSErr" and node.args):
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            msg = arg.value
        elif isinstance(arg, ast.JoinedStr):
            # f-strings: keep literal parts, show interpolations as {...}
            msg = _fstring_text(arg)
        else:
            continue
        msg = " ".join(msg.split())
        if SKIP.match(msg):
            continue
        out.append(msg)
    # de-dup, keep first occurrence order
    seen = set()
    uniq = []
    for m in out:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return sorted(uniq)


def _fstring_text(node):
    """Rebuild an f-string as a template: `cannot read '{path}'`."""
    parts = []
    for v in node.values:
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            parts.append(v.value)
        elif isinstance(v, ast.FormattedValue):
            try:
                parts.append("{" + ast.unparse(v.value) + "}")
            except Exception:
                parts.append("{...}")
        else:
            parts.append("{...}")
    return "".join(parts)


def main():
    lines = ["# error catalog (generated — do not edit by hand)",
             "",
             "> จาก `scripts/gen_errors.py` โดยอ่าน `HSErr(...)` ทุกตัวใน",
             "> `interp.py`, `hs.py`, `x64gen.py`, `fmt.py`, `ir.py`, `irx64.py`",
             "> (regen: `python3 scripts/gen_errors.py`, เทสตรวจด้วย `tests/test_docs.py`)",
             "",
             "ทุก error เป็น Str `\"<message> at line N\"` — ไม่มี exception object,",
             "จับได้ด้วย `try/except as e`, ไม่จับ = พิมพ์ `error: <msg> at line N`",
             "ที่ stderr แล้ว exit 1. `{...}` ในตารางคือค่าที่แทนที่ตอนรัน",
             "",
             "หา error ของตัวเอง: `python3 scripts/lsp_client.py --diag prog.hs`",
             "(0-based line) หรือ `python3 hs.py --json check prog.hs`",
             "",
             "## error ที่เจอบ่อยที่สุด",
             "",
             "| รหัส | ข้อความ | แปลว่า | แก้ยังไง |",
             "|---|---|---|---|",
             "| `E001` | `cannot add Int and Str` | ผสมชนิดใน `+` | แปลงเอง: `str(x) + str(y)` |",
             "| `E002` | `index out of range` | `a[i]` นอกช่วง | เช็ค `len(a)` ก่อน |",
             "| `E003` | `key '<k>' not found` | อ่าน Dict key ที่ไม่มี | ใช้ `exists`-like logic หรือ default |",
             "| `E004` | `unknown variable '<n>'` | ยังไม่เคย assign | สร้างก่อนใช้ (โดยเฉพาะฝั่ง x64) |",
             "| `E005` | `not callable: <t>` | เรียกค่าที่ไม่ใช่ฟังก์ชัน | ตรวจชนิดก่อนเรียก |",
             "| `E006` | `expression expected` | syntax ขาด/ผิดบรรทัด | ดูเลขบรรทัดใน error |",
             "| `E007` | `expected ':' then an indented block` | ลืม `:` ท้ายบรรทัด | เติม `:` + indent |",
             "| `E008` | `unexpected indent` | มีช่องว่างนำหน้าเกิน | จัดรูปด้วย `hs fmt` |",
             "| `E009` | `assertion failed at line N` | เงื่อนไขใน `unsafe:` ไม่ผ่าน | เช็คชนิดใน `unsafe:` |",
             "| `E010` | `extern handled elsewhere or not in x64 subset` | ใช้ `extern:` ฝั่ง x64 | ดู `x64-subset.md` |",
             "| `E011` | `json_parse not in x64 subset` | ใช้ `json_*` ฝั่ง x64 | ดู `x64-subset.md` |",
             "| `E012` | `cannot find module '<m>'` | `import` หาไฟล์ไม่เจอ | ตั้ง `HSPATH` ให้ชี้โฟลเดอร์ที่มีโมดูล |",
             ""]
    total = 0
    for path, title in SOURCES:
        msgs = messages(path)
        total += len(msgs)
        lines.append(f"## {title} ({len(msgs)})")
        lines.append("")
        for m in msgs:
            lines.append(f"- `{m}`")
        lines.append("")
    lines.append(f"รวม {total} ข้อความ — ข้อความซ้ำข้ามไฟล์ถูกนับทีเดียวต่อไฟล์")
    docs = os.path.join(ROOT, "docs")
    with open(os.path.join(docs, "errors.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote docs/errors.md ({total} messages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
