# JIT corpus parity gate

`tests/test_jit_corpus.py` builds the eager in-process JIT driver
(`selfhost/be/jit_run.holy`) once and runs every runnable `tests/*.holy`
through both the interpreter and the JIT, comparing exit code, stdout, and
stderr byte for byte. It is the phase-4 corpus gate from the roadmap: the
corpus is the whole `tests/` tree, and every entry must be classified.

## Buckets

- **parity** — byte-identical to the interpreter. This is the gate; any new
  `tests/*.holy` lands here by default.
- **divergence** — a documented difference, asserted *not* to be byte-equal.
  When a divergence gets fixed, the test fails on purpose until the entry is
  moved to parity here.

`mod_*.holy` helpers and `*.nativeonly` programs are not run directly, the
same convention as `tests/test.py` and `tests/test_native.py`. The fixture
HTTP server for `t_sock` and the `/tmp/opencode/hs_fs_test` pre-clean for
`t_fs` follow the other runners.

## Current divergences

| test | reason |
| --- | --- |
| `err_umix` | The interpreter rejects I64+U64 mixing; the x64 subset accepts it (roadmap 3.4 — needs an owner decision). |
| `t_bits` | 62-bit x64 Int vs 64-bit interpreter Int (roadmap 3.4 — needs an owner decision). |
| `t_circ` | The interpreter nests `in module '...'` prefixes on loader errors; the self-hosted loader reports the innermost error only. |
| `t_ffi` | The JIT driver cannot bind C-source externs (`extern from "file.c"`); library externs work, and the Python native path covers C sources via gcc (`test_native.py`). |
| `t_sock` | The self-hosted x64 backend has no socket/http/ticks runtime support yet; the Python native path covers it (`test_native.py`). |

## Driver error surfacing

`jit_run.holy` reports target compile errors exactly like the interpreter:
`error: {msg} at line {line}` on stderr with exit code 1. Two quirks of the
self-hosted toolchain are handled in the driver rather than in shared code:

- `hs` appends ` at line N` (the driver's own source line) to every raised
  string, so plain raises from `parselib` arrive with the target line baked
  into the message plus a driver-line suffix; the driver strips the outer
  suffix only when two are present.
- `pyrt.py_err` strings carry the target line after a `u0002` marker, and
  `pyrt.py_eline`'s `j + 1` skip reads the marker's own digits (`0002` plus
  the line), so the driver parses the encoded line itself.
