"""Reference token dump for selfhost/lex.hs (interp's own lexer)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import interp


def esc(s):
    return (s.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")
            .replace("\r", "\\r").replace("\0", "\\0"))


def main(path):
    src = open(path, encoding="utf-8", newline="").read()
    try:
        toks = interp.lex(src)
    except interp.HSErr as e:
        print(f"error: {e.msg} at line {e.line}")
        return 1
    out = []
    for t in toks:
        if t.k == "NUM":
            v = t.raw if t.raw is not None else str(t.v)
        elif t.k == "STR":
            v = esc(t.v)
        elif t.k == "FSTR":
            v = esc(t.v)
        else:
            v = t.v
        out.append(f"{t.k}\t{v}\t{t.line}")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
