"""Shared corpus divergence pins: tests/corpus_pins.py

Single source of truth for the documented interp-vs-native divergences in
the tests/*.holy corpus. Every corpus gate (test_jit_corpus.py live
differential, test_golden.py frozen-golden parity) asserts these entries are
NOT byte-equal to the interp reference, so a future fix forces
reclassification here and in docs/jit-corpus.md.
"""

DIVERGENCE = {
    "err_umix": "interp rejects I64+U64 mixing; the x64 subset accepts it "
                "(roadmap 3.4, needs an owner decision)",
    "t_bits": "62-bit x64 Int vs 64-bit interpreter Int "
              "(roadmap 3.4, needs an owner decision)",
    "t_ffi": "the JIT driver cannot bind C-source externs "
             "(extern from \"file.c\"); library externs work and the Python "
             "native path covers C sources via gcc (test_native.py)",
    "t_sock": "the self-hosted x64 backend has no socket/http/ticks runtime "
              "support yet; the Python native path covers it (test_native.py)",
}
