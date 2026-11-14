"""CPython tokenize oracle for selfhost/py/pylex_run.holy (3.11 semantics).

Prints KIND<TAB>value<TAB>line per token: NAME->ID, NUMBER->NUM,
STRING->STR/BYTES/FSTR (raw spelling kept), OP->OP, NEWLINE/INDENT/DEDENT,
ENDMARKER->EOF. COMMENT and NL are dropped (pylex never emits them).
Values are backslash-escaped the same way pylex_run.holy does.
"""
import io
import sys
import tokenize


def esc(s):
    return (s.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")
            .replace("\r", "\\r").replace("\0", "\\0"))


def main(path):
    src = open(path, encoding="utf-8", newline="").read()
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        t = tok.type
        s = tok.string
        if t in (tokenize.COMMENT, tokenize.NL, tokenize.ENCODING):
            continue
        if t == tokenize.NAME:
            k = "ID"
        elif t == tokenize.NUMBER:
            k = "NUM"
        elif t == tokenize.STRING:
            body = s.lstrip("rRbBfF")
            pre = s[:len(s) - len(body)].lower()
            k = "FSTR" if "f" in pre else ("BYTES" if "b" in pre else "STR")
        elif t == tokenize.OP:
            k = "OP"
        elif t == tokenize.NEWLINE:
            k = "NEWLINE"
            s = ""
        elif t == tokenize.INDENT:
            k = "INDENT"
            s = ""
        elif t == tokenize.DEDENT:
            k = "DEDENT"
            s = ""
        elif t == tokenize.ENDMARKER:
            k = "EOF"
            s = ""
        else:
            k = "ERRORTOKEN" if t == tokenize.ERRORTOKEN else "TOKEN%d" % t
        out.append("%s\t%s\t%d" % (k, esc(s), tok.start[0]))
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
