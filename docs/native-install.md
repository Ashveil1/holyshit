# Native install and run/build route

From the source checkout on Linux x86-64:

```sh
sh scripts/install-native.sh "$HOME/holyshit-native"
"$HOME/holyshit-native/bin/hs" run examples/hello.holy
"$HOME/holyshit-native/bin/hs" build examples/hello.holy /tmp/hello-hs
```

The parent must already exist and the destination must not. Paths with spaces
work. The installer checks the host and delegates to the audited bundle
builder: verify pinned compiler checksum, stage a separate directory, build
the eager driver with the native compiler, then publish without overwriting.
It downloads nothing, uses no Python/gcc, changes no profile/PATH, creates no
system-wide link and needs no sudo. It can take time to compile the driver.

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

Check/fmt/test/REPL/LSP and source/bootstrap audits remain development tools
that use Python. Kernel building has its existing separate native script;
it is not an installed launcher command. Python reference/testing tools are
kept deliberately and are not being deleted in this stage.
