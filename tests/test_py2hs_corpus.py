#!/usr/bin/env python3
"""py2hs frozen corpus: byte-exact goldens + fail-closed diagnostics.

tests/py2hs_corpus/<name>.py is the input. A sibling <name>.holy pins the
translator output byte for byte; a sibling <name>.fail pins the diagnostic
detail (everything after the "Type:line " prefix of the first error) for a
rejected input, and additionally pins that the reject leaves earlier good
top-level definitions in the output and drops the bad one.

The corpus is the C2 contract: the hs port of py2hs (selfhost/py/) must
reproduce these goldens exactly before mkbe can switch pipelines.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import py2hs

CORPUS = ROOT / "tests" / "py2hs_corpus"
ASM = ROOT / "x64.py"


def main():
    inputs = sorted(CORPUS.glob("*.py"))
    assert inputs, "corpus missing"
    total = 0
    for inp in inputs:
        name = inp.stem
        golden = inp.with_suffix(".holy")
        reject = inp.with_suffix(".fail")
        assert golden.exists() != reject.exists(), name
        out = CORPUS / (name + ".out.tmp")
        try:
            errs = py2hs.translate([str(inp)], str(out), str(ASM))
            text = out.read_text() if out.exists() else ""
            if golden.exists():
                assert not errs, (name, errs)
                assert text == golden.read_text(), name
            else:
                assert errs, (name, "expected rejection")
                detail = reject.read_text().rstrip("\n")
                assert any(e.split(" ", 1)[1] == detail for e in errs if " " in e), (name, errs, detail)
                # fail-closed: a "good" def present in every reject input
                # survives; the rejected construct's name does not.
                assert "good = 7" in text, (name, text)
                assert "bad" not in text, (name, text)
            total += 1
        finally:
            if out.exists():
                out.unlink()
    print(f"{total}/{total} py2hs corpus byte-exact goldens + fail-closed diagnostics")


if __name__ == "__main__":
    main()
