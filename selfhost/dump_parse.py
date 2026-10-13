"""Reference AST dump for selfhost/parse.hs (interp.parse_program as JSON)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import interp


def main(path):
    src = open(path, encoding="utf-8", newline="").read()
    try:
        interp.reset_parse_state()
        body = interp.parse_program(src)
    except interp.HSErr as e:
        print(f"error: {e.msg} at line {e.line}")
        return 1
    print(json.dumps(body, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
