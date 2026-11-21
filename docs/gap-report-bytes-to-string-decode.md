# Runtime gap report (candidate): Bytes-to-String UTF-8 decode builtin

**From:** agent lane (local AI agent, `agent/`)
**To:** language/runtime lane (`interp.py`, native x64 backend, self-interpreter)
**Date:** 2026-11-21
**Status:** NOT blocking - the agent lane ships a pure-hs workaround
(`agent/utf8.holy`). Filed so the language lane has the full picture.

## Summary

`tcp_recv` and `http_get` return the Bytes type, but no builtin converts
Bytes to a String (`str(b)` yields the Python-style `b'...'` repr via
`disp()`, and there is no `chr`/codepoint builtin, so hs code cannot even
assemble characters from codes). Any hs program that wants to *process*
network or binary-file text - not just print its repr - needs a decoder.

## Workaround shipped in the agent lane

`agent/utf8.holy`: `utf8_decode(bytes)` in pure hs on `byte_at` +
literal one-character tables (ASCII 32-126, Latin-1 0xA0-0xFF, Thai
U+0E00-0E7F; everything else including invalid bytes, overlongs,
surrogates and 4-byte codepoints becomes U+FFFD). Verified byte-exact
against Python's UTF-8 decode on a 64 KiB mixed ASCII/Thai/Latin-1
payload, on both the interp and native x64 routes.

Measured cost at the A18 64 KiB extraction cap:

| route | time for 64 KiB |
|---|---|
| interp.py (hosted interpreter) | ~1.24 s |
| native x64 | ~5 ms |

The interp cost is tolerable for a user-invoked page fetch but would be
the wrong tool for bulk text. The per-call `byte_at` overhead dominates.

## Why a builtin is still wanted

1. **Coverage:** the table approach covers the scripts the agent needs
   today (ASCII/Latin-1/Thai) but every other script decodes as U+FFFD.
   A real builtin decodes all of UTF-8.
2. **Performance:** ~1.2 s per 64 KiB on the interpreter is 250x the
   native cost; a builtin is a memmove-class operation.
3. **Correctness surface:** hand-rolled decoders are a classic place
   for security bugs (overlongs, surrogates, truncation). One audited
   runtime implementation beats one per application.
4. **Parity:** the workaround's output is route-identical today
   (verified), but a builtin makes that guarantee the runtime's, with
   the bytes/string duality (`len` counting chars on interp, bytes on
   native) documented in one place.

## Suggested semantics

`utf8_decode(bytes) -> Str`: strict-by-default with U+FFFD replacement
for invalid sequences (never raise on network data), or a two-mode
`utf8_decode(bytes, "replace"|"strict")` at the language lane's
discretion. Must behave identically on every route, with the result's
`len`/`find`/slicing following each route's existing char/byte model
as documented.

## Out of scope

Encoding (String to Bytes), other encodings than UTF-8, and the
private-network guard / bounded-recv reports (filed separately).
