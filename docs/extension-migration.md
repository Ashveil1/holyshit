# Source extension transition

Canonical tracked source filenames use `.holy`. The `.hs` suffix remains
legacy-compatible. Parser syntax, AST, module names and `hs.py` are unchanged.

Reference interpreter/IR, GCC, Python x64 and hosted native import lookup try
`.holy` then `.hs` within each directory while preserving directory priority.
The small cc compiler has the same suffix preference within its narrower
source-directory-only import subset. Import syntax does not include a suffix.
A directory containing both resolves one file, never a merged module.

Examples, benchmarks, eval reference solutions, bootstrap/runtime paths and
editor file associations use `.holy`. Editor setups retain `.hs` as an alias.
Test discovery checks both, and compatibility tests deliberately create legacy
files. Example/benchmark discovery refuses to pass vacuously with no sources.

The source move requires a freshly source-built and audited compiler seed:
independent Python stage zero equals the proposed seed; native generations
repeat; moved native bundles self-compile without the checkout. Changing only
the filename or checksum is not an audit. Full CI must pass before acceptance.

No legacy deprecation/removal date is set. Removing `.hs` support is a later
explicit compatibility decision. A new suffix does not itself create a
GitHub-recognized language name, language statistics or syntax highlighting.
