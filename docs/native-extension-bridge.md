# Native source-extension bridge

The x64 AST/IR compilers and hosted compiler now try `.holy` then `.hs`
within each source/HSPATH/working directory. Earlier directories still win.
Dotted imports use the same directory mapping. Neither parser nor ABI changes.
No tracked source file is renamed in this stage. The small legacy cc compiler
still needs separate resolver work before the final source migration.

The candidate seed was built from source with Python stage zero. It is not
accepted merely because its hash was changed. Full CI must compare it with a
fresh independent source build, compile another native generation, compare
bytes, and pass Python-free stages two/three and moved-bundle self-compilation.
A local native self-compilation overran a bounded105second session; this was
not a proven fixed point. The separate tests/test_hosted_seed.py gate owns
acceptance. Existing seed provenance and verification procedures stay intact.

Generation of be.hs remains exact through scripts/mkbe.sh with the maintained
forward-only zero-fuzz patch. The compact candidate expression intentionally
preserves source line counts: the translator uses line-derived temporary
identities and changing them adds unrelated generated-code churn.
