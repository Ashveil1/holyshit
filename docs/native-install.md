# Native install and run/build route

From the source checkout on Linux x86-64:

```sh
sh scripts/install-native.sh "$HOME/holyshit-native"
"$HOME/holyshit-native/bin/hs" run examples/hello.holy
"$HOME/holyshit-native/bin/hs" build examples/hello.holy /tmp/hello-hs
"$HOME/holyshit-native/bin/hs" interpret examples/hello.holy
```

The parent must already exist and the destination must not. Paths with spaces
work. The installer checks the host and delegates to the audited bundle
builder: verify pinned compiler checksum, stage a separate directory, build
the eager driver and the existing hs-written IR interpreter with the native
compiler, then publish without overwriting. Both drivers must build before
the staged directory is published; failure leaves no partial installation.
It downloads nothing, uses no Python/gcc, changes no profile/PATH, creates no
system-wide link and needs no sudo. Building both drivers takes additional
installation time and disk space; neither is rebuilt for each invocation.

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

Check/fmt/test/REPL/LSP and source/bootstrap audits remain development tools
that use Python. Kernel building has its existing separate native script;
it is not an installed launcher command. Python reference/testing tools are
kept deliberately and are not being deleted in this stage.
