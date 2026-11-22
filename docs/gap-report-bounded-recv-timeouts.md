# Runtime gap report: bounded receive timeouts for socket reads

**From:** agent lane (local AI agent, `agent/`)
**To:** language/runtime lane (`interp.py`, native x64 backend, self-interpreter)
**Date:** 2026-11-21
**Blocks:** agent A18 (URL reading) production release; A18 ships EXPERIMENTAL
with a documented hang risk until this lands

## Summary

`tcp_recv` and the `http_get` receive loop can block forever. The only
timeout anywhere in the hosted socket path is the 20-second connect
timeout in `socket.create_connection`; once connected, a peer that
sends nothing, stalls mid-response, or drips one byte per minute holds
the agent (and its whole REPL) indefinitely. For an interactive agent
that may run unattended, an unbounded fetch is a production blocker.
Timeouts are not implementable in the agent lane: hs has no clock
builtin usable for deadlines (`ticks` exists but `tcp_recv` blocks
inside the runtime, so hs code never gets a chance to check one), and
no non-blocking or select/poll builtin exists.

## Affects

- `interp.py` `b_tcp_recv` (line 3219): plain `s.recv(...)` on a socket
  with no timeout set.
- `interp.py` `b_http_get` (line 3288): recv loop with no idle or
  overall bound.
- Native x64 backend socket path: same question at kernel TCP level.
- Self-interpreter route if TCP-capable.

## Current behavior

1. Connect: bounded (20s, hosted).
2. After connect: unbounded. A silent or stalling peer hangs the
   process; only a signal or peer close ends the wait.
3. No way for hs code to cancel an in-progress read or bound a whole
   multi-recv fetch.

## Requirements (binding, from the A18 design review)

1. **Idle timeout:** a maximum time between received bytes (suggested
   default 10s). A peer that goes silent mid-response fails the read.
2. **Overall fetch deadline:** a maximum total time for a complete
   fetch operation (suggested default 30s), across however many recv
   calls it takes, so a slow-drip peer cannot stay under the idle
   timeout forever.
3. **Cancellation/close semantics:** on either timeout the operation
   fails, the socket is closed, and no partial result is returned -
   the caller sees a clean error, never truncated data.
4. **Distinct, stable error strings** for `connect timeout`,
   `idle timeout`, and `deadline exceeded` so callers and tests can
   tell them apart.
5. **Consistent across every networking-capable route** (interp,
   native x64, self-interpreter if TCP-capable), same defaults, same
   errors.
6. Configuration is acceptable as optional builtin arguments
   (e.g. `tcp_recv(sock, n, idle_ms)`) or runtime-level defaults, at
   the language lane's discretion; `http_get` must be bounded by
   default with no opt-out.

## Suggested hosted implementation sketch

Set `SO_RCVTIMEO` on sockets at creation (maps idle timeout to
`socket.timeout`), track the overall deadline with `time.monotonic()`
in the `http_get` loop and across consecutive `tcp_recv` calls (or
document that per-call idle is the only bound for raw sockets and give
`http_get` both). Close the socket on any timeout before raising.

## Test requirements (fixture server driven, all routes)

- **no-response:** accepts the connection, sends nothing -> idle
  timeout.
- **partial-stall:** sends headers then stops -> idle timeout.
- **slow-drip:** sends one byte per second indefinitely -> overall
  deadline exceeded (never the idle timeout).
- **oversized:** sends more than the caller's size cap at full speed ->
  caller's cap fires first (regression guard that timeouts do not
  break the fast path).
- **premature-close:** closes mid-body -> clean incomplete-response
  error, not a hang, not partial data.

## Out of scope

The agent-side 1 MiB byte cap and 64 KB extraction cap (agent lane,
A18.1), the private-network guard (separate gap report), and TLS.
