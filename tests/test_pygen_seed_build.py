#!/usr/bin/env python3
"""pygen seed build (C2.6): the hosted seed compiles the translator identically.

mkbe.sh builds selfhost/py/pygen_run.holy with bootstrap/hs-hosted-x86_64
(no Python in that step). This pins that the seed-built translator binary is
byte-identical to the `hs.py xbuild` product (the path tests/
test_pygen_native.py differentiates against the py2hs.py oracle on the whole
corpus), plus a behavior smoke: a golden input, a reject pin, and the
fail-closed survival pin through the seed-built binary.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRIVER = ROOT / "selfhost" / "py" / "pygen_run.holy"
SEED = ROOT / "bootstrap" / "hs-hosted-x86_64"
ASM = ROOT / "x64.py"
CORPUS = ROOT / "tests" / "py2hs_corpus"


def main():
    assert SEED.exists(), "hosted seed missing"
    with tempfile.TemporaryDirectory() as tmp:
        seed_exe = Path(tmp) / "pygen_seed"
        xbuild_exe = Path(tmp) / "pygen_xbuild"
        r = subprocess.run([str(SEED), str(DRIVER), str(seed_exe)],
                           capture_output=True, text=True, errors="replace")
        assert r.returncode == 0, r.stderr
        r = subprocess.run([sys.executable, str(ROOT / "hs.py"), "xbuild",
                            str(DRIVER), "-o", str(xbuild_exe)],
                           capture_output=True, text=True, errors="replace")
        assert r.returncode == 0, r.stderr
        assert seed_exe.read_bytes() == xbuild_exe.read_bytes(), \
            "seed and xbuild translator binaries diverge"
        print("ok   seed-built translator == xbuild-built translator")
        total = 1
        # behavior smoke through the seed-built binary: one golden, one reject
        golden_in = CORPUS / "class_inherit.py"
        out = Path(tmp) / "golden.holy"
        r = subprocess.run([str(seed_exe), str(golden_in), str(out), str(ASM)],
                           capture_output=True, text=True, errors="replace")
        assert r.returncode == 0 and not r.stdout, (r.stdout, r.stderr)
        assert out.read_text() == (CORPUS / "class_inherit.holy").read_text()
        total += 1
        reject_in = CORPUS / "fail_yield.py"
        out = Path(tmp) / "reject.holy"
        r = subprocess.run([str(seed_exe), str(reject_in), str(out), str(ASM)],
                           capture_output=True, text=True, errors="replace")
        assert r.returncode == 0, r.stderr
        detail = (CORPUS / "fail_yield.fail").read_text().rstrip("\n")
        uns = [l[len("UNSUPPORTED "):] for l in r.stdout.splitlines()
               if l.startswith("UNSUPPORTED ")]
        assert any(e.split(" ", 1)[1] == detail for e in uns if " " in e), uns
        assert "good = 7" in out.read_text() and "bad" not in out.read_text()
        total += 1
        print(f"{total}/{total} seed-built translator identical + behavior smoke")


if __name__ == "__main__":
    main()
