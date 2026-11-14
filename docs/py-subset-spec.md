# Python subset accepted by py2hs (C2 spec)

`scripts/py2hs.py` translates the Python emitter modules (`x64gen.py`,
`irx64.py`, style-compatible inputs) into hs. This document is the written
spec of the accepted subset; `tests/py2hs_corpus/` is the executable contract
(byte-exact goldens + fail-closed diagnostics, gated by
`tests/test_py2hs_corpus.py`).

The C2 hs port (`selfhost/py/`) must reproduce the corpus byte for byte.
Anything outside this subset is rejected with an `UNSUPPORTED` diagnostic,
never silently translated.

Measured corpus (x64gen.py + irx64.py + x64.py + py2hs.py, CPython 3.11 AST):
153,068 nodes, 77 distinct node types, 7 classes, 0 floats, 0 async/yield/
match/global/nonlocal, 23 integer literals >= 2^62, spaces-only indentation.

## Lexical rules

- Spaces-only indentation (no tabs in the corpus), 4-space convention.
- Comments and blank lines carry no semantics.
- String literals: single/double/triple quoted, `r`/`b`/`f` prefixes,
  backslash escapes. Non-ASCII bytes appear only inside strings/comments.
- Integer literals: decimal/hex/octal/binary with `_` separators. Values in
  [2^63, 2^64) map to their signed 64-bit twin (`v - 2^64`, emitted as
  `(0 - N)` when negative). No float literals occur in the corpus; a float
  constant is emitted via Python `repr` (pinned here, unused by the corpus).
- Implicit line joining inside `()[]{}`, explicit backslash continuation.

## Module level

Only these top-level statements are translated:

- `NAME = expr` (simple name target only - top-level tuple unpacking is
  rejected as `target Tuple`)
- `def` / `class` definitions
- `if` / `while` / `for` / `try` statements
- `import` / `from-import` / expression statements: dropped (this includes
  `if __name__ == "__main__":` blocks and docstrings)

A top-level statement that fails translation rolls back atomically: output
keeps earlier statements, drops the failed one, and records
`Type:line detail` in the returned error list.

## Statements

- Assign: single target, chained (`a = b = v` lowers right-to-left), tuple
  unpacking inside function bodies (`x, y = v` via a positional temp).
  Tuple-target assignment where the name is later used as a dict/set key
  goes through `py_key`.
- AugAssign: `+ - * & | ^ << >> // %`. Pow-augment is rejected.
- if/elif/else, while, for (`range`, arbitrary iterables, tuple targets one
  level deep plus one nested pair - three levels deep is `deep for target`).
- try/except (`except T as e` -> `except as e`), finally.
- `with open(...) as f:` -> `py_open`/`py_close` bracket; other with-items
  rejected.
- `raise`, `raise expr`, `assert` (-> `py_assert`), `del d[k]`,
  pass/break/continue, return.
- Expression statements: `xs.pop()` -> slice-shorten; `d.pop(k, dflt)` ->
  `d[k] = null`; `s.discard(x)` -> `s[x] = false`; other calls emitted as
  expressions; bare constants dropped.
- Rejected: yield/await/global/nonlocal, `del` of non-subscripts,
  `with` on non-open, starred targets.

## Expressions

- Constants, names (with alias substitution), attributes.
- Binary: `+ - * & | ^ << >>` direct; `//` -> `py_floordiv`; `**` -> `py_pow`;
  `%` direct except `str % args` -> `py_percent`; sequence repetition
  (`[0]*n`, `"ab"*3`, `b"x"*8`) -> `py_rep`; set-literal union -> `py_union`;
  `x & 0xFFFFFFFFFFFFFFFF` elides the mask.
- Unary: `-x` -> `(0 - x)`, `~x`, `not x`, `+x`.
- BoolOp `and`/`or` chains; Compare chains; `in`/`not in` (tuple keys via
  `py_key`); `is`/`is not`; `is True`/`is False` gain a `py_type` bool check.
- IfExp, Subscript (index, `a:b`, `:b` -> `0:b`, `a:`/`[:]` -> `py_tail`;
  any explicit slice step is rejected), Tuple/List/Set (`py_set`), Dict
  (tuple keys -> `py_key`; `**` rejected), Lambda, NamedExpr (emits a
  pending assignment before the enclosing line).
- Comprehensions: list/set (`py_set`)/dict (`py_dict`)/generator (as list),
  exactly one generator and at most one `if` filter; tuple loop targets
  destructure through a positional `_pN_g` temp (N = current output line -
  name shape is pinned by the corpus).
- f-strings: literal + `str(value)` parts; `!r` -> `py_repr`; `:spec` ->
  `py_fmt`.

## Calls and names

- Positional args always. Keyword args require the callee's signature
  (collected from the same translation unit, `x64.py`'s Asm class, or a
  method table): reordered into position, skipped parameters before the last
  given keyword become `null`; keywords `encoding`/`file` are dropped.
  Kwargs on an unknown callee are rejected.
- `print(...)` -> `py_print([...])`; `len`/`range`/`str`/`int`/`float`
  pass through; `HSErr` -> `py_err`; `isinstance(x, T)`/`(T1, T2)` ->
  `py_isinstance(x, ["T"])`; the FUNCS/METHODS/MODFUNCS tables in py2hs.py
  map Python builtins/methods to `py_*` helpers (`selfhost/be/pyrt.holy`);
  `struct.pack/pack_into/unpack` -> `py_pack*`; `os`/`sys`/`re` attribute
  calls -> `py_<mod>_<attr>`; `os.path.*` -> `py_os_path_*`.
- Asm methods (from `x64.py`'s Asm class): `obj.m(...)` -> `asm.m(...)` with
  `lea_m` 5-arg reordering to `asm.lea_mx` and `resolve` 2-arg -> `resolve_at`;
  plain `alias = obj.m` binds the name as an alias.
- `append` -> `append(list, x)`; `split`/`join`/`find` -> `py_split`/
  `py_join`/`py_find`; other known methods via the METHODS table; unknown
  attribute calls go to `recv.attr(...)` with a `_rN` receiver temp for
  non-name receivers.
- Method-default padding: PAD-table helpers are right-padded with `null`;
  methods with Python defaults are padded from the recorded default
  expressions at call sites missing trailing args.
- Reserved/builtin collisions: `HS_RESERVED | HS_BUILTINS` names gain a
  trailing `_` (locals/params). Top-level def/class collisions keep their
  name and emit a `name-collision` warning (side channel).

## Classes

- Method definitions; class-body constant assigns hoist to
  `Class_CONST` module bindings (tuple destructuring via a `_c_Class_name`
  temp); nested classes hoist to `Outer_Inner` siblings; single inheritance
  `class D(B)`; `Class(...)` construction -> `Class__init__(recv, ...)`.
- `self.K` for a hoisted constant reads `Class_K`; `Gen.Scope` is special
  cased to `Gen_Scope` construction.
- A method that fails translation is replaced by
  `def m(...): raise "untranslated m"` and recorded in the error list;
  sibling methods survive.
