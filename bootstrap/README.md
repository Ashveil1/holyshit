# Hosted compiler seed

The source of the hosted compiler is `selfhost/be/compile.hs` and its hs
imports. The Python implementation stays as the semantic/test reference.

The Linux x86-64 seed `hs-hosted-x86_64` is pinned by `SHA256SUMS`.
It was accepted after the native compiler passed full CI and its source
bootstrap/fixed-point gates. `scripts/verify-hosted-seed.py` compares it to
a compiler built from this source before executing it, then checks another
generation. That audit uses Python as the independent reference.

For Python-free bootstrap, run `scripts/bootstrap-seed.sh [output-dir]`.
It checks the pinned hash before executing the seed, builds stages two and
three and requires both to match the seed byte for byte. The seed is Linux
x86-64 only, 9,158,232 bytes. It uses the repository source and runtime data;
it is not a standalone distribution. To rebuild without trusting the seed,
use `scripts/bootstrap-hosted.sh` (Python stage zero, native later stages).

SHA256: `93895ed3382737908f92bfc466b3569f839e030b0c362ff39f3980353b1104e6`.
Changing compiler sources may change the fixed point. Regenerate and verify
the seed rather than silently accepting an old binary or updating the hash.

The hosted compiler is not the kernel compiler. Its full-width unsafe
literal gate now covers decimal and hex words through 64 bits. Safe tagged
integer behavior is unchanged. Kernel compilation is a separate artifact.
