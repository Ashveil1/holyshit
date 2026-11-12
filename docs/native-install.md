# Native install and run/build route

From the source checkout on Linux x86-64:

```sh
sh scripts/install-native.sh "$HOME/holyshit-native"
"$HOME/holyshit-native/bin/hs" run examples/hello.holy
"$HOME/holyshit-native/bin/hs" build examples/hello.holy /tmp/hello-hs
"$HOME/holyshit-native/bin/hs" interpret examples/hello.holy
"$HOME/holyshit-native/bin/hs" fmt examples/hello.holy
"$HOME/holyshit-native/bin/hs" check examples/hello.holy
"$HOME/holyshit-native/bin/hs" test examples
```

The parent must already exist and the destination must not. Paths with spaces
work. The installer checks the host and delegates to the audited bundle
builder: verify pinned compiler checksum, stage a separate directory, build
the eager driver, existing hs-written IR interpreter, hs formatter, hs
checker, hs tester and hs explainer with the native compiler, then publish
without overwriting. All six must build before the staged directory is
published; failure leaves no partial installation.
It downloads nothing, uses no Python/gcc, changes no profile/PATH, creates no
system-wide link and needs no sudo. Building six drivers takes additional
installation time and disk space; none is rebuilt for each invocation.

Keep the whole installed directory together. The launcher resolves compiler,
source/runtime data and driver relative to itself; it does not rely on the
original checkout. It verifies binary checksums before execution. Checksums
are accidental-corruption checks, not protection if an attacker replaces
both a binary and its checksum. The compiler seed's independent source and
fixed-point audits are separate CI gates, not performed by every install.

Updates install into another new directory. Check the new install before
switching your own command/PATH; the old directory remains a rollback. No
in-place upgrade, automatic removal or persistent cache is added. Removing an
install is the user's removal of that one directory. Do not delete a source
checkout or another installation to make room without an explicit decision.

`run SOURCE [args...]` uses the prebuilt eager driver. Target source is still
compiled each run, but the driver is built only once at installation. `build
SOURCE OUTPUT` uses the native hosted compiler. Both retain the documented
hosted subset; there is no interpreter fallback, full-language parity or
cross-platform claim. The build output behavior is unchanged.

`interpret SOURCE [args...]` explicitly selects the existing hs-written IR
interpreter, prebuilt at installation. It supports the documented dynamic core,
imports and supported builtins, with runtime errors and argument forwarding.
Unsupported unsafe/FFI operations (including in imports) refuse before target
effects with exit code 3. Parse/runtime failures use exit code 1; a missing
source argument uses exit code 2. See [the interpreter subset](irinterp.md).
This is neither JIT nor a universal language-parity claim. No automatic fallback
is added to `run` or `build`. The interpreter driver checksum is checked before
every launch, with the same accidental-corruption limits described above.
A successful check adds no target stdout/stderr. A missing source file fails
through the existing driver with status 1. A missing interpreter binary or
checksum file reports an incomplete install; install a new complete bundle.
An older bundle has no `interpret` command and must also be replaced with a
new install, rather than copying a launcher into it.

`fmt SOURCE` prints comment-preserving formatted text to stdout without running
or editing the source. It always selects the existing formatter's `--comments`
mode. Exactly one source is required: missing source or any extra argument
(including `-w`, `--check`, `--comments` or another file) returns status 2.
This is not recursive formatting, a canonical-format check or write-in-place.
Do not redirect stdout to the same source file: the shell would truncate it
before the formatter reads it. Blank lines are dropped and comments can move,
including to the end for some headers/declarations. See the
[formatter placement limits](cheatsheet.md#optional-hs-source-formatter-comments).
UTF-8 comment text is covered, not general Unicode/parser/newline parity.
A successful checksum check adds no stdout/stderr. Parse/read failures retain
the source formatter's status 1 and diagnostic streams, which can include an
error line on stdout as well as stderr, not the Python CLI's error contract.
Missing formatter binary/manifest or checksum corruption refuses with status 1.
Old bundles without `fmt` require a new complete install, not a copied launcher.
Formatter corruption does not block `run`, `build` or `interpret`.

`check SOURCE` scans the source and its reachable imports without running any
of them, using the prebuilt checker. A clean scan prints `ok: SOURCE` to stdout
with exit 0; a check error prints the same file/line/message text as the Python
CLI's check to stderr with exit 1. `hs --json check SOURCE` (or `--json` after
the command) emits the JSON error object with file, line and message, plus
the error catalog's code/hint fields when a coded catalog row matches, like
the Python CLI.
The checker keeps the Python checker's documented baseline: unknown names,
bare raise, def-after-use and circular imports are accepted, not errors. A
missing source argument returns status 2; extra positional arguments are
ignored like the Python CLI. The checker checksum is verified before every
launch with the same accidental-corruption limits above. A missing checker
binary or manifest, or checksum corruption, refuses with status 1 and reports
an incomplete bundle; install a new complete bundle. Checker corruption does
not block `run`, `interpret`, `fmt`, `test`, `explain` or `build`.

`test FILE|DIR...` runs every top-level zero-arg `def test_*` of each given
file; a directory means its recursively discovered test_*/t_* .holy/.hs
files, like the Python CLI. A test passes by returning and fails by raising.
Output and exit codes match the Python CLI: `ok   FILE::NAME` and
`FAIL FILE::NAME: error` lines, a `N passed, M failed` summary, exit 1 on any
failure or when no tests ran, and `--json` for the same machine-readable
object the Python CLI prints. Tests execute one generated sibling driver file
per source file on the installed hs interpreter, so the file's top-level code
runs once and imports resolve as usual. Deviation from the Python CLI: the
installed interpreter has the documented irinterp subset, so files using
unsafe/ffi or out-of-subset builtins are reported failed with the refusal
line instead of executing; the Python CLI runs them under CPython. Discovery
uses the system `find` utility. The tester checksum is verified before every
launch with the same accidental-corruption limits above; a missing tester
binary or manifest, or checksum corruption, refuses with status 1. Tester
corruption does not block `run`, `interpret`, `fmt`, `check`, `explain` or
`build`.

`explain "<error message>"` explains a message against the shipped error
catalog (docs/errors.md, installed alongside the bundle): it prints the best
catalog hit with its meaning and fix, or `no catalog entry` plus similar
patterns, exactly like the Python CLI, with `--json` for the same
machine-readable object. Exit 0 on a hit, 1 on no hit, 2 on a missing
message. Message words are passed exactly as given (never resolved as
paths). The explainer checksum is verified before every launch with the same
accidental-corruption limits above; a missing explainer binary or manifest,
or checksum corruption, refuses with status 1. Explainer corruption does not
block `run`, `interpret`, `fmt`, `check`, `test` or `build`. The `--json run`
stderr envelope (a JSON error object for runtime errors) remains Python-only.

`cc SOURCE [-o OUTPUT]` compiles a program with the compiler written in hs
itself (selfhost/cc.holy), prebuilt at installation: the cc subset is
Int/Bool/Str/List/Dict, functions, modules and try/except; Float, class and
FFI are compile errors, never silently different output. The output is a
static x86-64 ELF with no runtime dependency, written executable. The default
output path strips the source's final extension, and `-o` is accepted
anywhere after the source with other extra arguments ignored, like the Python
CLI; a missing source argument returns status 2. Successful compiles emit no
stdout/stderr and produce byte-identical ELFs to the Python CLI's compiler
(the same cc.holy source compiled by itself). Compile-failure diagnostics
differ by executing runtime and both forms are pinned in
tests/test_native_cc.py: the Python CLI's self-compiled compiler reports some
failures as its own emitted runtime's uncatchable native faults (a fixed
`error: <reason>` line on stderr, empty stdout), while the installed
natively-compiled driver reports them through the hs-level handler (the
diagnostic on stdout, then `error: compile failed at line N` on stderr with
the native runtime's uncaught-raise line suffix). Exit codes match. The
compiler checksum is verified before every launch with the same
accidental-corruption limits above; a missing compiler binary or manifest,
or checksum corruption, refuses with status 1. Compiler corruption does not
block `run`, `interpret`, `fmt`, `check`, `test`, `explain` or `build`.

`--version` (or `-V`) prints `hs ` plus the bundled VERSION file's contents
wherever the flag appears, like the Python CLI.

REPL/LSP and source/bootstrap audits remain development tools
that use Python. The Python formatter remains available for `-w`/`--check`. Kernel building has its existing separate native script;
it is not an installed launcher command. Python reference/testing tools are
kept deliberately and are not being deleted in this stage.
