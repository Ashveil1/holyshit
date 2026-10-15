# Source extension transition

The chosen extension is `.holy`. `.hs` remains legacy-compatible. This change
is about source filenames, not new syntax, a new AST or renaming `hs.py`.
GitHub naming/highlighting is a separate upstream language-recognition issue.

## Stage one

Reference interpreter/IR, GCC compilation and LSP import lookup try `.holy`
then `.hs` within each directory, while preserving directory priority.
`hs test` finds both extensions. Explicit filenames already work, including
formatter input. No tracked source is renamed yet. Native hs and x64 import
lookup is NOT bridged in this stage; do not distribute all-.holy source to
the existing pinned seed or claim all backends have migrated.

## Next gates

- Change Python x64 + generated native resolver together. Keep regeneration
  exact and the maintained patch forward-only without fuzz. Audit the newly
  built native seed against Python stage zero and another native generation.
- Prove mixed old/new imports, same-directory preference, earlier-directory
  legacy priority, dotted modules, missing modules and native bundle movement.
- Move sources with `git mv`, and update docs, scripts, tests and editor file
  associations. Retain temporary old-seed source access until the new compiler
  can build and run independently. Do not replace a seed hash without audit.
- Run full CI and bootstrap/kernel/JIT/bundle gates for each focused PR.
- Deprecate legacy suffix later, as a separate explicit compatibility change.

Never silently load both suffixes for one module. In a directory containing
both, `.holy` intentionally shadows `.hs`; they are not merged. A new suffix
does not promise a GitHub language bar named after this language.
