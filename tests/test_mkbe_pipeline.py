#!/usr/bin/env python3
"""mkbe pipeline (C2.7): the whole be.holy regeneration is Python-free.

scripts/mkbe.sh translates, patches and formats using only the hosted seed
(no python3 anywhere in the script). This pins that running it leaves
selfhost/be/be.holy byte-identical, i.e. the checked-in backend matches the
current translator sources, and that the postport patch applies cleanly.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BE = ROOT / "selfhost" / "be" / "be.holy"
REJ = ROOT / "selfhost" / "be" / "be.holy.rej"


def main():
    before = BE.read_bytes()
    try:
        r = subprocess.run(["sh", "scripts/mkbe.sh"], cwd=ROOT,
                           capture_output=True, text=True, errors="replace")
        assert r.returncode == 0, r.stdout + r.stderr
        assert BE.read_bytes() == before, "mkbe.sh changed be.holy"
        assert not REJ.exists(), "postport patch left rejects"
    finally:
        BE.write_bytes(before)
        if REJ.exists():
            REJ.unlink()
    print("1/1 mkbe.sh regenerates be.holy byte-identically (Python-free)")


if __name__ == "__main__":
    main()
