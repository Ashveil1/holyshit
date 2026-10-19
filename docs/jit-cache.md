# JIT compiled-code cache (`.hsc`)

The eager JIT driver (`selfhost/be/jit_run.holy`) compiles a program to an
in-memory x86-64 image on every run. Codegen is deterministic given the
inputs, so the driver snapshots the assembler state right after IR
generation into `<prog>.hsc` next to the source and reuses it while the
inputs are unchanged.

## What is cached

- The emitted code section, data section, labels, data labels and the
  relocation fixup table (all position-independent: every cross reference
  is RIP-relative and re-resolved by `jitimage.relocate` at publish time).
- The extern metadata (`ffi_libs`, `ffi_syms`, `ffi_owners`). Libraries are
  re-`dlopen`ed and every GOT slot re-`dlsym`ed on each run, so bound
  addresses are always fresh.

## What is never cached

- The argv/env trampoline (rebuilt per run from `argv()` and
  `/proc/self/environ`).
- dlopen handles, GOT pointers, mmap addresses.

## Keying and invalidation

The cache stores every input file that fed the image - the program, each
module `GenIR` loaded, and the embedded `runtime/json.holy` helper when
`json_*` is used - with a dual FNV-1a content hash. A hit re-reads and
re-hashes those files only; any content change, missing file, format
version bump, truncation or corruption falls back to a full compile. Writes
go to a temporary file and are renamed into place; a program that fails to
compile leaves no cache. When the directory is not writable the run
proceeds uncached.

`jitcache.FORMAT` is the cache format version. Bump it whenever codegen or
the assembler emission changes in a way that makes older snapshots
incompatible - the driver binary itself is not part of the key.
