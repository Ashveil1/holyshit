# Hosted compiler seed

The source of the hosted compiler is `selfhost/be/compile.hs` and its hs
imports. The Python implementation stays as the semantic/test reference.

A seed is accepted only after the current native compiler passes full CI
and the stage1/stage2/stage3 byte-equality gate. This directory does not yet
contain a binary seed. Until it does, use `scripts/bootstrap-hosted.sh` to
build stage1 with Python and stage2/stage3 with the native compiler.

The hosted compiler is not the kernel compiler. Its full-width unsafe
literal gate now covers decimal and hex words through 64 bits. Safe tagged
integer behavior is unchanged. Kernel compilation is a separate artifact.
