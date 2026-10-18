#!/usr/bin/env python3
"""Build ai/wnn/data/connectome.txt from the Cook et al. 2019 connectome.

Source: wormwiring.org "SI 5 Connectome adjacency matrices, corrected
July 2020" (https://www.wormwiring.org/pages/adjacency.html), hermaphrodite
chemical (directed) + gap junction (symmetric) matrices. Rows presynaptic,
columns postsynaptic, weights in EM serial sections.

Output format: line 1 = "N M", line 2 = N cell names, then M lines
"pre post weight c|g" (gap junctions stored once, undirected).
"""
import sys, io, urllib.request, openpyxl

URL = ("https://www.wormwiring.org/si/"
       "SI%205%20Connectome%20adjacency%20matrices,%20corrected%20July%202020.xlsx")

def edges(ws, tag):
    rows = list(ws.iter_rows(values_only=True))
    cols = [str(x).strip() if x is not None else None for x in rows[2]]
    out = []
    for row in rows[3:]:
        pre = row[2] if len(row) > 2 else None
        if pre is None:
            continue
        pre = str(pre).strip()
        for j in range(3, len(row)):
            v = row[j]
            post = cols[j] if j < len(cols) else None
            if v is None or post is None:
                continue
            try:
                w = int(v)
            except (ValueError, TypeError):
                continue
            if w > 0:
                out.append((pre, post, w, tag))
    return out

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src is None:
        print("downloading", URL)
        data = urllib.request.urlopen(URL).read()
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
    else:
        wb = openpyxl.load_workbook(src, read_only=True)
    all_edges = edges(wb["hermaphrodite chemical"], "c")
    all_edges += edges(wb["hermaphrodite gap jn symmetric"], "g")
    names = {}
    for pre, post, w, t in all_edges:
        for n in (pre, post):
            if n not in names:
                names[n] = len(names)
    seen = set()
    final = []
    for pre, post, w, t in all_edges:
        if t == "g":
            key = (min(pre, post), max(pre, post))
            if key in seen:
                continue
            seen.add(key)
        final.append((names[pre], names[post], w, t))
    out = sys.argv[2] if len(sys.argv) > 2 else "connectome.txt"
    with open(out, "w") as f:
        f.write(f"{len(names)} {len(final)}\n")
        f.write(" ".join(sorted(names, key=lambda n: names[n])) + "\n")
        for a, b, w, t in final:
            f.write(f"{a} {b} {w} {t}\n")
    print(f"{len(names)} cells, {len(final)} connections -> {out}")

if __name__ == "__main__":
    main()
