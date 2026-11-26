#!/usr/bin/env python3
"""A18.2 bounded-transport tests for the repl read-url path, against
the timing routes of tests/fix_fetch_server.py.

Runs each leg through two routes:
  1. python3 interp.py agent/repl.holy   (reference interpreter)
  2. natively compiled agent/repl.holy   (hs.py build; needs
     CPATH/LIBRARY_PATH pointing at the gc toolchain, same as
     tests/test_agent_core.py)
both with HS_AGENT_TEST_FETCH=1 (agent-side unlock) and
HS_ALLOW_PRIVATE_NET=1 (runtime netguard override for the loopback
fixture - an explicit override for isolated tests, never normal
operation). Flags are passed per-subprocess, so the parent process env
never mutates and there is nothing to restore on failure.

Pinned behavior (interp and native must agree on the reason strings):
  silent peer / header stall / partial-body stall -> "idle timeout"
  1 B/s drip and near-idle 1 B/9s drip -> "deadline exceeded"
    (the agent-side absolute 30s deadline, checked before and after
    every receive; until tcp_recv accepts a per-call timeout the
    deadline is SOFT: a blocking receive may overrun it by up to one
    10s idle interval - hence the wide upper windows)
  undeclared length streaming past the cap -> "response too large"
  declared Content-Length exactly 1 MiB accepted at header time (the
  short body then fails as "incomplete response"); 1 MiB + 1 is
  rejected unread (fast return proves the body was never read)
  premature close -> "incomplete response", nothing is stored, the
  socket is cleaned up, and the next command answers normally
Every leg has an outer subprocess safety timeout and the fixture
server is killed in a finally. This suite is slow (~4 min): it is
registered in run_all.SUITES and listed in run_all.QUICK_SKIP.
"""
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMFILE = os.path.join(ROOT, "agent-memory.json")

# (label, fixture paths, expected failure line, min seconds, max seconds)
LEGS = [
    ("silent", ["/timeout"], "read url: fetch failed: idle timeout", 8, 16),
    ("stall-headers", ["/stall-headers-only"],
     "read url: fetch failed: idle timeout", 8, 16),
    ("stall-partial-body", ["/stall-partial-body"],
     "read url: fetch failed: idle timeout", 8, 16),
    ("slow-drip", ["/slowdrip"],
     "read url: fetch failed: deadline exceeded", 29, 40),
    ("near-idle-drip", ["/drip9"],
     "read url: fetch failed: deadline exceeded", 29, 42),
    ("oversized-nocl", ["/oversized-nocl"],
     "read url: fetch failed: response too large (over 1 MiB)", 0, 20),
    ("cl-exact-1mib", ["/cl-exact"],
     "read url: fetch failed: incomplete response", 0, 10),
    ("cl-plus1-unread", ["/cl-plus1"],
     "read url: fetch failed: response too large (over 1 MiB)", 0, 5),
]


def start_server():
    p = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "tests", "fix_fetch_server.py"), "0"],
        stdout=subprocess.PIPE, text=True)
    line = p.stdout.readline().split()
    assert line and line[0] == "listening", "fixture server did not start"
    return p, int(line[1])


def run_leg(argv, port, paths, env):
    cmds = "".join("read url http://127.0.0.1:%d%s\n" % (port, p)
                   for p in paths) + "quit\n"
    if os.path.exists(MEMFILE):
        os.remove(MEMFILE)
    t0 = time.monotonic()
    r = subprocess.run(argv, input=cmds, capture_output=True, text=True,
                       env=env, cwd=ROOT, timeout=90)
    dt = time.monotonic() - t0
    if os.path.exists(MEMFILE):
        os.remove(MEMFILE)
    return r, dt


def check_leg(route, label, paths, want, lo, hi, argv, port, env):
    r, dt = run_leg(argv, port, paths, env)
    assert r.returncode == 0, (route, label, r.returncode, r.stderr[-2000:])
    assert want in r.stdout, (route, label, "missing failure line",
                              want, r.stdout[-1500:])
    assert lo <= dt <= hi, (route, label, "outside window",
                            dt, lo, hi)
    print("ok %s %s (%s, %.1fs)" % (route, label, want.rsplit(" ", 3)[-1], dt))


def check_premature_close(route, argv, port, env):
    r, dt = run_leg(argv, port, ["/partial-close", "/clean"], env)
    assert r.returncode == 0, (route, r.returncode, r.stderr[-2000:])
    assert "read url: fetch failed: incomplete response" in r.stdout, (
        route, r.stdout[-1500:])
    # nothing was stored for the failed fetch: the next successful
    # read is url-1, and it answers normally (socket cleanup proven)
    assert "experimental: url-1:" in r.stdout, (route, r.stdout[-1500:])
    print("ok %s premature-close (nothing stored, next command works, %.1fs)"
          % (route, dt))


def main():
    backup = None
    if os.path.exists(MEMFILE):
        backup = open(MEMFILE, "rb").read()
        os.remove(MEMFILE)
    srv, port = start_server()
    try:
        env = dict(os.environ, HS_AGENT_TEST_FETCH="1",
                   HS_ALLOW_PRIVATE_NET="1")
        routes = [("interp", [sys.executable,
                              os.path.join(ROOT, "interp.py"),
                              os.path.join(ROOT, "agent", "repl.holy")])]
        with tempfile.TemporaryDirectory() as td:
            binpath = os.path.join(td, "agentrepl")
            b = subprocess.run([sys.executable, os.path.join(ROOT, "hs.py"),
                                "build", os.path.join(ROOT, "agent", "repl.holy"),
                                "-o", binpath],
                               capture_output=True, text=True,
                               env=dict(os.environ))
            assert b.returncode == 0, (
                "native build failed (CPATH/LIBRARY_PATH gc toolchain "
                "env needed, same as tests/test_agent_core.py): "
                + b.stderr[-2000:])
            routes.append(("native", [binpath]))
            for route, argv in routes:
                for label, paths, want, lo, hi in LEGS:
                    check_leg(route, label, paths, want, lo, hi,
                              argv, port, env)
                check_premature_close(route, argv, port, env)
    finally:
        srv.kill()
        if backup is not None:
            open(MEMFILE, "wb").write(backup)
        elif os.path.exists(MEMFILE):
            os.remove(MEMFILE)
    print("all agent.fetch bounded-transport tests passed")


if __name__ == "__main__":
    main()
