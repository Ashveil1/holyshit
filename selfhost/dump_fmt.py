"""Reference formatter output for selfhost/fmt.hs (fmt.py on interp's AST)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fmt
import interp


def main(path):
    src = open(path, encoding="utf-8", newline="").read()
    try:
        interp.reset_parse_state()
        out = fmt.fmt_program(interp.parse_program(src, raw=True))
    except interp.HSErr as e:
        print(f"error: {e.msg} at line {e.line}")
        return 1
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
