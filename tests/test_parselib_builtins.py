#!/usr/bin/env python3
"""parselib reserved-name sync gate: the selfhost parser's BUILTINS list must
equal the reference interpreter's BUILTINS exactly, so a struct name is
reserved identically by both parsers."""
import os
import re
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import interp

src = open(os.path.join(ROOT, "selfhost/parselib.holy"), encoding="utf-8").read()
m = re.search(r'BUILTINS = \[(.*?)\]', src, re.S)
assert m, "parselib.holy BUILTINS list not found"
parselib = set(re.findall(r'"([a-z_0-9]+)"', m.group(1)))
reference = set(interp.BUILTINS)
missing = sorted(reference - parselib)
extra = sorted(parselib - reference)
assert not missing and not extra, f"parselib BUILTINS out of sync: missing={missing} extra={extra}"
print(f"1/1 parselib BUILTINS == interp.BUILTINS ({len(reference)} names, strict equality)")
