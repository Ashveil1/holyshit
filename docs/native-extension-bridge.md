# Native source-extension bridge

The x64 AST/IR compilers and hosted compiler try `.holy` then `.hs` within
each source/HSPATH/working directory. Earlier directories still win. Dotted
imports use the same directory mapping. Parser and ABI are unchanged. The
small cc compiler separately bridges its source-directory-only resolver.

Tracked source now uses `.holy`. Runtime JSON and compiler sources move with
it. The matching candidate seed is built from source with Python stage zero,
then full CI must independently compare it with a fresh source build, compile
another native generation, compare bytes and pass Python-free stages two/three
and moved-bundle self-compilation before acceptance. No changed checksum alone
establishes trust or fixed-point correctness.

Generation of be.holy stays exact through scripts/mkbe.sh with the maintained
forward-only zero-fuzz patch. Its compact candidate expression intentionally
preserves source line counts: the translator uses line-derived temporary
identities and changing them adds unrelated generated-code churn.
