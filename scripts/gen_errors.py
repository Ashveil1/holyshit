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
    ("interp.py", "interp.py - interpreter + parser (every language error)"),
    ("hs.py", "hs.py - native backend via gcc"),
    ("x64gen.py", "x64gen.py - direct x86-64 backend (xbuild/xkernel)"),
    ("fmt.py", "fmt.py — formatter"),
    ("ir.py", "ir.py - middle IR (build/verify/exec)"),
    ("irx64.py", "irx64.py - IR to x86-64"),
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
             "> From `scripts/gen_errors.py`, reading every `HSErr(...)` in",
             "> `interp.py`, `hs.py`, `x64gen.py`, `fmt.py`, `ir.py`, `irx64.py`",
             "> (regen: `python3 scripts/gen_errors.py`, checked by `tests/test_docs.py`)",
             "",
             "Every error is a Str `\"<message> at line N\"` - no exception object,",
             "catchable with `try/except as e`; uncaught = prints `error: <msg> at line N`",
             "to stderr and exits 1. `{...}` in the table is a value substituted at runtime",
             "",
             "Find your error: `python3 scripts/lsp_client.py --diag prog.holy`",
             "(0-based line) or `python3 hs.py --json check prog.holy`",
             "",
             "## Most common errors",
             "",
             "| Code | Message | Meaning | Fix |",
             "|---|---|---|---|",
             "| `E001` | `cannot add Int and Str` | mixed types in `+` | convert explicitly: `str(x) + str(y)` |",
             "| `E002` | `index out of range` | `a[i]` out of range | check `len(a)` first |",
             "| `E003` | `key '<k>' not found` | reading a missing Dict key | use exists-like logic or a default |",
             "| `E004` | `unknown variable '<n>'` | never assigned | create before use (especially on x64) |",
             "| `E005` | `not callable: <t>` | calling a non-function value | check the type before calling |",
             "| `E006` | `expression expected` | missing/wrong syntax on the line | see the line number in the error |",
             "| `E007` | `expected ':' then an indented block` | forgot `:` at end of line | add `:` + indent |",
             "| `E008` | `unexpected indent` | extra leading whitespace | reformat with `hs fmt` |",
             "| `E009` | `assertion failed at line N` | a condition in `unsafe:` failed | check types in `unsafe:` |",
             "| `E010` | `extern handled elsewhere or not in x64 subset` | using `extern:` on the x64 side | see `x64-subset.md` |",
             "| `E011` | `json_parse not in x64 subset` | using `json_*` on the x64 side | see `x64-subset.md` |",
             "| `E012` | `cannot find module '<m>'` | `import` cannot find the file | set `HSPATH` to point at the module's directory |",
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
    lines.append(f"{total} messages total - duplicates across files are counted once per file")
    docs = os.path.join(ROOT, "docs")
    with open(os.path.join(docs, "errors.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote docs/errors.md ({total} messages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
