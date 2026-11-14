#!/usr/bin/env python3
"""pygen native (C2.5): xbuild-compiled pygen_run matches py2hs.py byte for byte.

The mkbe.sh translate step runs the hs port of py2hs as a native x86_64
binary (python3 hs.py xbuild selfhost/py/pygen_run.holy). This differential
compiles it once, then checks the frozen corpus (goldens byte-exact, fail
pins, fail-closed) and the real targets x64.py, irx64.py, x64gen.py plus the
mkbe multi-source form - translated text AND WARNING/UNSUPPORTED streams
against the py2hs.py oracle, mirroring tests/test_pygen.py (interp path).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import py2hs

DRIVER = ROOT / "selfhost" / "py" / "pygen_run.holy"
CORPUS = ROOT / "tests" / "py2hs_corpus"
ASM = ROOT / "x64.py"
TARGETS = [ROOT / f for f in ("x64.py", "irx64.py", "x64gen.py")]
MULTI = [tuple(ROOT / f for f in ("x64gen.py", "irx64.py"))]


def run_oracle(srcs, out):
    warns = []
    errs = py2hs.translate([str(s) for s in srcs], str(out), str(ASM), warns)
    return ["WARNING " + w for w in warns] + ["UNSUPPORTED " + e for e in errs]


def main():
    total = 0
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "pygen_native"
        r = subprocess.run(
            [sys.executable, str(ROOT / "hs.py"), "xbuild", str(DRIVER), "-o", str(exe)],
            capture_output=True, text=True, errors="replace")
        assert r.returncode == 0, r.stderr

        def run_native(srcs_csv, out):
            return subprocess.run([str(exe), srcs_csv, str(out), str(ASM)],
                                  capture_output=True, text=True, errors="replace")

        inputs = sorted(CORPUS.glob("*.py"))
        assert inputs, "corpus missing"
        for inp in inputs:
            name = inp.stem
            golden = inp.with_suffix(".holy")
            reject = inp.with_suffix(".fail")
            out = Path(tmp) / (name + ".holy")
            r = run_native(str(inp), out)
            assert r.returncode == 0, (name, r.stdout, r.stderr)
            lines = r.stdout.splitlines()
            text = out.read_text() if out.exists() else ""
            orc = Path(tmp) / (name + ".orc")
            assert lines == run_oracle([inp], orc), (name, lines)
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
                assert "good = 7" in text, (name, text)
                assert "bad" not in text, (name, text)
            total += 1
        print(f"ok   pygen-native corpus ({total} inputs)")
        for grp in [tuple([t]) for t in TARGETS] + list(MULTI):
            label = ",".join(p.name for p in grp)
            mine = Path(tmp) / "mine.holy"
            orc = Path(tmp) / "orc.holy"
            r = run_native(",".join(str(p) for p in grp), mine)
            assert r.returncode == 0, (label, r.stdout, r.stderr)
            assert r.stdout.splitlines() == run_oracle(grp, orc), label
            assert mine.read_text() == orc.read_text(), label
            total += 1
            print(f"ok   pygen-native {label}")
    print(f"{total}/{total} pygen native corpus + targets byte-exact vs py2hs.py")


if __name__ == "__main__":
    main()
