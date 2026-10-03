#!/usr/bin/env python3
"""Verify the docs are real, not aspirational.

    python3 tests/test_docs.py

Checks:
  1. every ```hs block in docs/*.md really produces the `# =>` output
  2. lang_data.BUILTINS covers interp.BUILTINS exactly (docs drift guard)
  3. docs/builtins.md + docs/api.json are up to date (regen and diff)
  4. every file linked from README.md / docs/index.md exists
  5. docs/lsp.md commands listed actually run
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import interp
import lang_data

DOCS = os.path.join(ROOT, "docs")

fails = 0
total = 0


def check(name, cond, detail=""):
    global fails, total
    total += 1
    if cond:
        print(f"ok   {name}")
    else:
        print(f"FAIL {name} {detail}")
        fails += 1


# ---------- 1. run every ```hs block ----------

def blocks(md):
    """yield (path, lineno, code, expected) for each ```hs block."""
    with open(md, encoding="utf-8") as f:
        lines = f.read().split("\n")
    i = 0
    while i < len(lines):
        if lines[i].strip() == "```hs":
            start = i
            j = i + 1
            while j < len(lines) and lines[j].strip() != "```":
                j += 1
            body = lines[i + 1:j]
            code, want = [], []
            for ln in body:
                if ln.startswith("# =>"):
                    want.append(ln[4:].strip())
                else:
                    code.append(ln)
            yield md, start + 1, code, want
            i = j
        i += 1


def run_blocks(state, path):
    """Run all blocks of one doc in order, threading state across blocks."""
    bad = []
    n = 0
    for md, lineno, code, want in blocks(md_path):
        n += 1
        src = "\n".join(code) + "\n"
        if not want:
            continue  # illustrative block, nothing to verify
        with tempfile.NamedTemporaryFile("w", suffix=".hs", dir=state,
                                         delete=False) as f:
            f.write(src)
            tmp = f.name
        try:
            # HSPATH -> repo so `import std.str` resolves inside doc examples
            env = dict(os.environ)
            env["HSPATH"] = ROOT + (":" + env["HSPATH"] if env.get("HSPATH")
                                    else "")
            p = subprocess.run([sys.executable, os.path.join(ROOT, "interp.py"),
                                tmp, path],
                               capture_output=True, text=True, timeout=60,
                               cwd=state, env=env)
            got = p.stdout.split("\n")
            got = [g for g in got if g != ""]
            exp = [w for w in want if w != ""]
            if got != exp:
                bad.append(f"{md}:{lineno} got={got} want={exp} err={p.stderr.strip()[:120]}")
        finally:
            os.unlink(tmp)
    return n, bad


with tempfile.TemporaryDirectory() as state:
    # only these are supposed to carry runnable examples
    must_have = {"tutorial.md", "x64-subset.md"}
    for fname in sorted(os.listdir(DOCS)):
        if not fname.endswith(".md") or fname.startswith("builtins"):
            continue
        md_path = os.path.join(DOCS, fname)
        n, bad = run_blocks(state, "a b c d e")
        if fname in must_have:
            check(f"{fname}: {n} hs block(s)", n > 0, "no ```hs block found")
        check(f"{fname}: output matches", not bad, "; ".join(bad))

# ---------- 2. builtin table covers the runtime ----------

interp_keys = set(interp.BUILTINS)
table_keys = set(lang_data.BUILTINS)
# pmm_total/pmm_free exist only in the freestanding kernel runtime
extra_ok = {"pmm_total", "pmm_free"}
check("lang_data covers interp.BUILTINS",
      not (interp_keys - table_keys),
      sorted(interp_keys - table_keys))
check("lang_data has no phantom builtins",
      not (table_keys - interp_keys - extra_ok),
      sorted(table_keys - interp_keys - extra_ok))

check("every builtin documented",
      all(sig and desc for sig, desc, _ in lang_data.BUILTINS.values()))
check("every builtin has backends",
      all(be for _, _, be in lang_data.BUILTINS.values()))
check("every keyword documented",
      all(v for v in lang_data.KEYWORDS.values()))

# ---------- 3. generated docs are current ----------

def regenerated(path, script):
    full = os.path.join(DOCS, path)
    before = open(full, encoding="utf-8").read()
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", script)],
                   capture_output=True, text=True, check=True)
    return before == open(full, encoding="utf-8").read()


check("docs/api.json current", regenerated("api.json", "gen_api.py"))
check("docs/builtins.md current", regenerated("builtins.md", "gen_api.py"))
check("docs/errors.md current", regenerated("errors.md", "gen_errors.py"))

data = json.load(open(os.path.join(DOCS, "api.json"), encoding="utf-8"))
check("api.json has version", bool(data.get("version")))
check("api.json builtins match table",
      set(data["builtins"]) == table_keys,
      sorted(set(data["builtins"]) ^ table_keys))

# ---------- 4. links exist ----------

def links(md):
    with open(os.path.join(ROOT, md), encoding="utf-8") as f:
        text = f.read()
    out = []
    for m in re.finditer(r"\]\(([^)#]+)\)", text):
        t = m.group(1)
        if t.startswith(("http://", "https://", "mailto:")):
            continue
        out.append(t)
    # backticked repo paths only: must contain a "/" so we don't chase
    # user-config filenames like `settings.json` or `test_fmt.py`
    for m in re.finditer(r"`((?:\.\./)?[A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+\.(?:hs|md|py|json|vim|toml|js))`",
                         text):
        out.append(m.group(1))
    return out


for src_doc in ("README.md", "docs/index.md", "docs/lsp.md",
                "docs/for-agents.md", "docs/stdlib.md", "docs/kernel.md",
                "docs/x64-subset.md", "docs/tutorial.md", "docs/cheatsheet.md",
                "editors/README.md", "examples/README.md", "AGENTS.md"):
    missing = []
    for t in links(src_doc):
        base = os.path.dirname(os.path.join(ROOT, src_doc))
        cand = os.path.normpath(os.path.join(base, t))
        if not os.path.exists(cand):
            # also try repo-root-relative (docs use bare names)
            cand2 = os.path.join(ROOT, t)
            if not os.path.exists(cand2):
                missing.append(t)
    check(f"{src_doc}: links exist", not missing, missing)

# ---------- 5. lsp.md commands work ----------

with tempfile.NamedTemporaryFile("w", suffix=".hs", delete=False) as f:
    f.write('def add(a, b):\n  return a + b\n\nprint add(1, 2)\n')
    prog = f.name
try:
    for args in (["--diag", prog], ["--symbols", prog],
                 ["--hover", prog, "4", "7"], ["--def", prog, "4", "7"],
                 ["--complete", prog, "4", "2"]):
        p = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "lsp_client.py")] + args,
            capture_output=True, text=True, timeout=60)
        check(f"lsp_client {' '.join(args[:1])}", p.returncode == 0,
              p.stderr.strip()[:200])
finally:
    os.unlink(prog)

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
