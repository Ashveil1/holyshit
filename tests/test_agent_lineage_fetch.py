#!/usr/bin/env python3
"""A19 corpus-lineage label tests: mixed corpus + HTTP evidence through
the repl's EXPERIMENTAL read-url path and the deterministic fixture
server (tests/fix_fetch_server.py), plus the core 'read corpus' route.

Pins the A19 section-6 compatibility contract:
  (a) corpus simplewiki-corpus + a fetched wikipedia.org page = ONE
      diversity group (publisher-lineage map v1), no MULTI_SOURCE, and
      no SINGLE_CORPUS (the side is not corpus-only);
  (b) corpus simplewiki-corpus + an unrelated domain = two groups,
      MULTI_SOURCE preserved;
  (c) HTTP-only behavior is pinned separately by test_agent_fetch.py,
      unchanged.

Determinism: HS_AGENT_TEST_FETCH=1 makes the fetch layer connect
non-loopback hosts to the local fixture server while keeping the
normalized URL as the source identity, so a 'wikipedia.org' page is
served locally.

Runs the script through two routes:
  1. python3 interp.py agent/repl.holy   (reference interpreter)
  2. natively compiled agent/repl.holy   (hs.py build; needs
     CPATH/LIBRARY_PATH pointing at the gc toolchain, same as
     tests/test_agent_core.py)
and asserts byte-identical, port-normalized transcripts against the
pinned EXPECTED below. Standalone harness (like test_agent_fetch.py):
not registered in run_all.SUITES.
"""
import difflib
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMFILE = os.path.join(ROOT, "agent-memory.json")

CMDS = ('read corpus simplewiki-corpus: robots are machines\n'
        'read url http://wikipedia.org:{PORT}/clean\n'
        'readings about robots\n'
        'read url http://127.0.0.1:{PORT}/dup\n'
        'readings about robots\n'
        'readings detail\n'
        'quit\n')

EXPECTED = ''  # pinned after the first verified run


def start_server():
    p = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "tests", "fix_fetch_server.py"), "0"],
        stdout=subprocess.PIPE, text=True)
    line = p.stdout.readline().split()
    assert line and line[0] == "listening", "fixture server did not start"
    return p, int(line[1])


def run(argv, inp, env, cwd):
    return subprocess.run(argv, input=inp, capture_output=True, text=True,
                          env=env, cwd=cwd, timeout=180)


def norm(out, port):
    return out.replace(":%d/" % port, ":PORT/")


def check(label, got):
    if got != EXPECTED:
        sys.stdout.writelines(difflib.unified_diff(
            EXPECTED.splitlines(True), got.splitlines(True),
            "expected", label))
        raise AssertionError(label + " transcript mismatch")
    print("ok", label, "transcript (%d bytes)" % len(got))


def main():
    # the repl persists agent-memory.json in its cwd; run both routes
    # against a clean memory file and restore whatever was there
    backup = None
    if os.path.exists(MEMFILE):
        backup = open(MEMFILE, "rb").read()
        os.remove(MEMFILE)
    srv, port = start_server()
    try:
        cmds = CMDS.replace("{PORT}", str(port))
        env = dict(os.environ, HS_AGENT_TEST_FETCH="1")

        # Environment probe: some sandboxes cannot tcp_connect at all
        # (the pinned A18.1 test_agent_fetch.py fails the same way
        # there). Skip cleanly instead of pinning a transcript no real
        # run produced.
        probe = run([sys.executable, os.path.join(ROOT, "interp.py"),
                     os.path.join(ROOT, "agent", "repl.holy")],
                    "read url http://127.0.0.1:%d/clean\nquit\n" % port,
                    env, ROOT)
        if "connect failed" in probe.stdout:
            print("skip: tcp_connect unavailable in this environment"
                  " (read url probe could not reach the local fixture"
                  " server); run where test_agent_fetch.py passes")
            return
        if os.path.exists(MEMFILE):
            os.remove(MEMFILE)
        if not EXPECTED:
            r = run([sys.executable, os.path.join(ROOT, "interp.py"),
                     os.path.join(ROOT, "agent", "repl.holy")],
                    cmds, env, ROOT)
            raise AssertionError(
                "EXPECTED transcript not pinned yet; verified actual "
                "was:\n" + norm(r.stdout, port))

        r = run([sys.executable, os.path.join(ROOT, "interp.py"),
                 os.path.join(ROOT, "agent", "repl.holy")], cmds, env, ROOT)
        assert r.returncode == 0, (r.returncode, r.stderr[-2000:])
        check("interp", norm(r.stdout, port))
        if os.path.exists(MEMFILE):
            os.remove(MEMFILE)

        with tempfile.TemporaryDirectory() as td:
            binpath = os.path.join(td, "agentrepl")
            b = subprocess.run([sys.executable, os.path.join(ROOT, "hs.py"),
                                "build", os.path.join(ROOT, "agent", "repl.holy"),
                                "-o", binpath],
                               capture_output=True, text=True, env=dict(os.environ))
            assert b.returncode == 0, (
                "native build failed (CPATH/LIBRARY_PATH gc toolchain "
                "env needed, same as tests/test_agent_core.py): "
                + b.stderr[-2000:])
            r = run([binpath], cmds, env, ROOT)
            assert r.returncode == 0, (r.returncode, r.stderr[-2000:])
            check("native", norm(r.stdout, port))
            if os.path.exists(MEMFILE):
                os.remove(MEMFILE)
    finally:
        srv.kill()
        if backup is not None:
            open(MEMFILE, "wb").write(backup)
        elif os.path.exists(MEMFILE):
            os.remove(MEMFILE)
    print("all agent.lineage-fetch semantic tests passed")


if __name__ == "__main__":
    main()
