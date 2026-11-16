#!/usr/bin/env python3
"""Rebase failing postport.patch hunks onto regenerated be.holy.

pygen renumbers generated temporaries (_tN, _pN_i) whenever x64gen.py
changes, which breaks the context lines of postport.patch. For each hunk
in the .rej file, find the region in the new be.holy that matches the
hunk's pre-image modulo temp names, then rewrite the hunk with the actual
new context/pre-image and rebase the temp names in the + lines.
"""
import re
import sys

BE = sys.argv[1] if len(sys.argv) > 1 else "selfhost/be/be.holy"
REJ = sys.argv[2] if len(sys.argv) > 2 else "selfhost/be/be.holy.rej"
PATCH = sys.argv[3] if len(sys.argv) > 3 else "selfhost/be/postport.patch"
OUT = sys.argv[4] if len(sys.argv) > 4 else "selfhost/be/postport.patch"

TEMP = re.compile(r"_[tp]\d+(?:_\d+)?\b")

be_lines = open(BE).read().split("\n")


def parse_hunks(text):
    hunks = []
    cur = None
    for line in text.split("\n"):
        if line.startswith("@@"):
            if cur:
                hunks.append(cur)
            cur = {"hdr": line, "lines": []}
        elif cur is not None and line[:1] in (" ", "-", "+", "\\"):
            cur["lines"].append(line)
    if cur:
        hunks.append(cur)
    return hunks


def find_preimage(hunk):
    """Locate the hunk's context/- lines in be_lines; return (start, tmpmap)."""
    pre = [l[1:] for l in hunk["lines"] if l[0] in (" ", "-")]
    # Build regex: escape, then swap temp tokens for named groups/backrefs.
    names = []

    def norm(line):
        out = []
        pos = 0
        for m in TEMP.finditer(line):
            out.append(re.escape(line[pos:m.start()]))
            tok = m.group(0)
            if tok not in names:
                names.append(tok)
                out.append("(?P<t%d>_[A-Za-z0-9_]+)" % names.index(tok))
            else:
                out.append("(?P=t%d)" % names.index(tok))
            pos = m.end()
        out.append(re.escape(line[pos:]))
        return "".join(out)

    pat = re.compile("\n".join(norm(l) for l in pre))
    hay = "\n".join(be_lines)
    m = pat.search(hay)
    if not m:
        return None, None
    start = hay[: m.start()].count("\n")
    tmpmap = {}
    for i, tok in enumerate(names):
        tmpmap[tok] = m.group("t%d" % i)
    return start, tmpmap


rej_hunks = parse_hunks(open(REJ).read())
patch_text = open(PATCH).read()
patch_hunks = parse_hunks(patch_text)

fixed = 0
for rh in rej_hunks:
    start, tmpmap = find_preimage(rh)
    if start is None:
        print("NO MATCH for", rh["hdr"])
        sys.exit(1)
    pre = [l[1:] for l in rh["lines"] if l[0] in (" ", "-")]
    n_pre = len(pre)
    n_del = len([l for l in rh["lines"] if l[0] == "-"])
    n_add = len([l for l in rh["lines"] if l[0] == "+"])
    # Actual current text of the region
    actual = be_lines[start:start + n_pre]
    # Rebase + lines through tmpmap
    def reb(line):
        def sub(m):
            return tmpmap.get(m.group(0), m.group(0))
        return TEMP.sub(sub, line)
    new_lines = []
    ai = 0
    for l in rh["lines"]:
        if l[0] == " ":
            new_lines.append(" " + reb(actual[ai]))
            ai += 1
        elif l[0] == "-":
            new_lines.append("-" + reb(actual[ai]))
            ai += 1
        else:
            new_lines.append("+" + reb(l[1:]))
    # Locate the corresponding hunk in postport.patch by payload: GNU patch
    # copies the hunk lines into the .rej verbatim (headers get renumbered).
    payload = tuple(l for l in rh["lines"] if l[0] in " -+")
    old_block = None
    for ph in patch_hunks:
        if tuple(l for l in ph["lines"] if l[0] in " -+") == payload:
            old_block = ph["hdr"] + "\n" + "\n".join(ph["lines"]) + "\n"
            break
    if old_block is None or old_block not in patch_text:
        print("PATCH HUNK NOT FOUND for", rh["hdr"])
        sys.exit(1)
    # New header: counts from line numbers
    mo = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", rh["hdr"])
    o_start, o_cnt = int(mo.group(1)), int(mo.group(2) or 1)
    delta = (start + 1) - o_start
    n_hdr = "@@ -%d,%d +%d,%d @@" % (
        start + 1, n_pre,
        int(mo.group(3)) + delta, n_pre - n_del + n_add)
    new_block = n_hdr + "\n" + "\n".join(new_lines) + "\n"
    patch_text = patch_text.replace(old_block, new_block, 1)
    fixed += 1
    print("rebased", rh["hdr"], "->", n_hdr)

open(OUT, "w").write(patch_text)
print(f"{fixed} hunks rebased")
