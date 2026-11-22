# Runtime gap report: DNS-safe private-network guard for outbound connects

**From:** agent lane (local AI agent, `agent/`)
**To:** language/runtime lane (`interp.py`, native x64 backend, self-interpreter)
**Date:** 2026-11-21
**Blocks:** agent A18 (URL reading) production release; A18 ships EXPERIMENTAL until this lands

## Summary

The agent's A18 milestone fetches user-supplied URLs (`read url <url>`).
Neither `http_get` nor `tcp_connect` restricts the destination address:
any hostname or IP the caller (or a DNS answer) resolves to is connected
to, including loopback, private, link-local, unspecified and multicast
addresses. This is a classic SSRF surface. The agent cannot fix this in
its own lane: hs code never sees the resolved IP, so application-side
checks would race DNS (rebinding). The guard must live in the runtime,
at connect time, identically on every networking-capable route.

## Affects

- `interp.py` `b_tcp_connect` (line 3196) and `b_http_get` (line 3288):
  both call `socket.create_connection((host, port), timeout=20)` with no
  address policy.
- Native x64 backend: `tcp_connect` / `http_get` are listed as supported
  (docs/builtins.md: interp ✓, native ✓).
- Self-interpreter route (`selfhost/be/irinterp*.holy`) if it implements
  the TCP builtins (capability currently being verified in A18.0).

## Current behavior

- `http_get` is http:// only, does not follow redirects, has no size
  cap, and connects to whatever the URL host resolves to.
- `tcp_connect` connects to any host/port with a 20s connect timeout.
- No route exposes the resolved address to hs code, so no application-
  level guard is possible.

## Security impact

A fetched page cannot redirect the agent anywhere (redirects already
error out), and A18 fetches only URLs the user typed verbatim, so the
practical exposure today is a user pasting a hostile link. Even so, a
`read url http://169.254.169.254/...` (cloud metadata), an internal
service on 10.x/192.168.x, or a DNS name that resolves to a private
address would all be fetched and read into the agent's evidence store.
Because the agent is meant to run unattended overnight, the destination
policy must not depend on the user reading every URL carefully.

## Requirements (binding, from the A18 design review)

1. **Consistent across every networking-capable route.** interp.py,
   native x64, and the self-interpreter if TCP-capable must enforce the
   same policy with the same error semantics, so route parity is
   testable.
2. **IPv4 and IPv6, including IPv4-mapped and IPv4-compatible forms**
   (`::ffff:127.0.0.1`, `::127.0.0.1`, `0:0:0:0:0:ffff:a00:1`, ...).
3. **Block:** loopback (`127.0.0.0/8`, `::1`), private (`10.0.0.0/8`,
   `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`), link-local
   (`169.254.0.0/16`, `fe80::/10`, which covers cloud metadata at
   169.254.169.254), unspecified (`0.0.0.0`, `::`), and multicast
   (`224.0.0.0/4`, `ff00::/8`).
4. **DNS-rebinding safe:** resolve, check every resolved address, and
   connect to the exact checked IP - no second resolution between check
   and connect. If any resolved address is blocked, the whole connect
   fails (fail closed).
5. **Test-only fixture exception** that ordinary commands cannot reach:
   the agent's deterministic fixtures serve from 127.0.0.1. Suggested
   mechanism: a process-level environment flag (e.g.
   `HS_ALLOW_PRIVATE_NET=1`) read by the runtime itself, never settable
   or observable-as-enabled from hs code, and documented as test-only.
6. **Error semantics:** a blocked destination raises a distinct,
   stable error string (e.g. `connect blocked: private address`) so
   callers can tell policy denials from network failures.

## Suggested semantics

- `http_get`: guard always on (it is a web-fetch convenience builtin;
  private-network fetching of fixtures goes through the test
  exception).
- `tcp_connect`: same guard by default. If the language lane wants
  general-purpose local TCP to keep working without the env flag, an
  explicit policy argument is acceptable, as long as `http_get` cannot
  reach it.
- The guard applies at every connect, not once per process.

## Test requirements

Per route, with and without the test exception: literal loopback IP,
literal private IPs (one per range), link-local metadata address,
IPv6 loopback, IPv4-mapped IPv6 loopback, a hostname resolving to a
private address (fixture DNS or hostmap hook), a hostname whose
addresses mix public and private (must fail closed), and the
rebinding case (address checked differs from address connected - the
implementation must connect to the checked IP).

## Out of scope

TLS/https (a separate, larger gap noted in the A18 proposal), DNS
filtering of public-but-hostile hosts, and any application-level URL
policy (the agent already restricts scheme/port/syntax in its own
lane).
