#!/usr/bin/env python3
"""pygen (C2.3): hs port of py2hs reproduces scripts/py2hs.py byte for byte.

Differential: selfhost/py/pygen_run.holy (via interp.py) vs scripts/py2hs.py
over the frozen py2hs corpus (goldens byte-exact, fail pins with exact
diagnostic details, fail-closed "good = 7" survives / "bad" dropped) and the
real translation targets x64.py, irx64.py, x64gen.py, where both the
translated text AND the WARNING/UNSUPPORTED diagnostic streams must match
the oracle exactly. This is the gate that lets mkbe switch pipelines without
regenerating the bootstrap seed.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import py2hs

INTERP = ROOT / "interp.py"
DRIVER = ROOT / "selfhost" / "py" / "pygen_run.holy"
CORPUS = ROOT / "tests" / "py2hs_corpus"
ASM = ROOT / "x64.py"
TARGETS = [ROOT / f for f in ("x64.py", "irx64.py", "x64gen.py")]


def run_mine(src, out):
    return subprocess.run(
        [sys.executable, str(INTERP), str(DRIVER), str(src), str(out), str(ASM)],
        capture_output=True, text=True, errors="replace")


def run_oracle(src, out):
    warns = []
    errs = py2hs.translate([str(src)], str(out), str(ASM), warns)
    return ["WARNING " + w for w in warns] + ["UNSUPPORTED " + e for e in errs]


def main():
    inputs = sorted(CORPUS.glob("*.py"))
    assert inputs, "corpus missing"
    total = 0
    for inp in inputs:
        name = inp.stem
        golden = inp.with_suffix(".holy")
        reject = inp.with_suffix(".fail")
        assert golden.exists() != reject.exists(), name
        out = CORPUS / (name + ".pygen.tmp")
        orc = CORPUS / (name + ".py2hs.tmp")
        try:
            r = run_mine(inp, out)
            assert r.returncode == 0, (name, r.stdout, r.stderr)
            lines = r.stdout.splitlines()
            text = out.read_text() if out.exists() else ""
            assert lines == run_oracle(inp, orc), (name, lines)
            if golden.exists():
                assert not any(l.startswith("UNSUPPORTED ") for l in lines), (name, lines)
                assert text == golden.read_text(), name
            else:
                uns = [l[len("UNSUPPORTED "):] for l in lines
                       if l.startswith("UNSUPPORTED ")]
                assert uns, (name, "expected rejection")
                detail = reject.read_text().rstrip("\n")
                assert any(e.split(" ", 1)[1] == detail for e in uns if " " in e), \
                    (name, uns, detail)
                # fail-closed: the "good" def present in every reject input
                # survives; the rejected construct's name does not.
                assert "good = 7" in text, (name, text)
                assert "bad" not in text, (name, text)
            total += 1
            print(f"ok   pygen {name}")
        finally:
            for p in (out, orc):
                if p.exists():
                    p.unlink()
    for tgt in TARGETS:
        mine = tgt.with_suffix(".pygen.tmp")
        orc = tgt.with_suffix(".py2hs.tmp")
        try:
            r = run_mine(tgt, mine)
            assert r.returncode == 0, (tgt, r.stdout, r.stderr)
            assert r.stdout.splitlines() == run_oracle(tgt, orc), tgt
            assert mine.read_text() == orc.read_text(), tgt
            total += 1
            print(f"ok   pygen {tgt.name}")
        finally:
            for p in (mine, orc):
                if p.exists():
                    p.unlink()
    print(f"{total}/{total} pygen corpus + targets byte-exact vs py2hs.py")


if __name__ == "__main__":
    main()
