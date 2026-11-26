#!/usr/bin/env python3
"""A18.1 semantic fetch tests: the repl's EXPERIMENTAL read-url path
against the deterministic fixture server (tests/fix_fetch_server.py).

Runs the same command script through two routes:
  1. python3 interp.py agent/repl.holy   (reference interpreter)
  2. natively compiled agent/repl.holy   (hs.py build; needs
     CPATH/LIBRARY_PATH pointing at the gc toolchain, same as
     tests/test_agent_core.py)
both with HS_AGENT_TEST_FETCH=1 (agent-side unlock) and
HS_ALLOW_PRIVATE_NET=1 (runtime netguard unlock: since #449 the runtime
itself blocks loopback/private connects at connect time, and hs code
cannot set process env, so the fixture needs the env exception), and
asserts byte-identical,
port-normalized transcripts against the pinned EXPECTED below. The
transcript pins: clean 3-candidate extraction, hostile script/style
stripping + inert command text, fake USER_CONFIRMED staying
UNVERIFIED, modal/quoted skip classes, every failure reason
(301/302/404, oversized body, oversized content-length, bigheaders,
chunked, binary, incomplete, malformed), Thai UTF-8 decoding,
url-N dedup with fetch counts, query redaction, transactional
failures (failed fetches never appear in the registry), and the
no-flag policy rejections (private IPs, non-80 ports). A18.2 adds:
duplicate content-length / content-type rejections, content-encoding
rejection, a header terminator split across two TCP segments,
byte-fragment assembly (no full-read assumption), a fragment leg
(#frag stripped at normalize time, so the re-read dedups to the same
url-N), and no-flag odd IPv4 spellings (127.1, 2130706433) blocked by
the RUNTIME guard with the mapped reason "private address blocked".
"""
import difflib
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMFILE = os.path.join(ROOT, "agent-memory.json")

CMDS = 'read url http://127.0.0.1:{PORT}/clean\nread url http://127.0.0.1:{PORT}/hostile\nis a car a bird?\nreadings\nread url http://127.0.0.1:{PORT}/fake-confirm\nis a kiwi a bird?\nread url http://127.0.0.1:{PORT}/modal\nread url http://127.0.0.1:{PORT}/redirect301\nread url http://127.0.0.1:{PORT}/redirect302\nread url http://127.0.0.1:{PORT}/notfound\nread url http://127.0.0.1:{PORT}/oversized\nread url http://127.0.0.1:{PORT}/bigheaders\nread url http://127.0.0.1:{PORT}/chunked\nread url http://127.0.0.1:{PORT}/binary\nread url http://127.0.0.1:{PORT}/partial-close\nread url http://127.0.0.1:{PORT}/malformed\nread url http://127.0.0.1:{PORT}/cl-oversized\nread url http://127.0.0.1:{PORT}/thai\nread url http://127.0.0.1:{PORT}/thai-mixed\nread url http://127.0.0.1:{PORT}/dup\nread url http://127.0.0.2:{PORT}/dup\nreadings detail\nread url http://127.0.0.1:{PORT}/dup-cl\nread url http://127.0.0.1:{PORT}/dup-ct\nread url http://127.0.0.1:{PORT}/gzip\nread url http://127.0.0.1:{PORT}/queryecho?token=secret123\nread url http://127.0.0.1:{PORT}/queryecho?token=secret123#frag\nread url http://127.0.0.1:{PORT}/thai\nreadings detail\nread url http://127.0.0.1:{PORT}/split-headers\nread url http://127.0.0.1:{PORT}/tiny-fragments\nreadings\nquit\n'

EXPECTED = 'holyshit agent v0.17 - type \'help\' for commands, \'quit\' to leave\nexperimental: url-1: 3 segments in, 3 pattern matches, 3 candidates extracted (3 new, 0 updated, 0 refused, 0 repeat), 0 skipped (0 quoted, 0 directive, 0 modal-hedged, 0 multi-clause, 0 thai-boundary-ambiguous), 0 unmatched\nexperimental: url-2: 5 segments in, 1 pattern matches, 1 candidates extracted (1 new, 0 updated, 0 refused, 0 repeat), 4 skipped (0 quoted, 4 directive, 0 modal-hedged, 0 multi-clause, 0 thai-boundary-ambiguous), 0 unmatched\nnot that i know\n4 read candidates (unverified readings, not facts):\n(a) robots | is-a | machines - positive support: 1 source (url-1); UNVERIFIED\n(b) birds | has | wings - positive support: 1 source (url-1); UNVERIFIED\n(c) snakes | has | legs - negative support: 1 source (url-1); UNVERIFIED\n(d) a kiwi | is-a | a bird - positive support: 1 source (url-2); UNVERIFIED\nexperimental: url-3: 2 segments in, 1 pattern matches, 1 candidates extracted (1 new, 0 updated, 0 refused, 0 repeat), 1 skipped (0 quoted, 0 directive, 0 modal-hedged, 1 multi-clause, 0 thai-boundary-ambiguous), 0 unmatched\nnot that i know\nexperimental: url-4: 4 segments in, 1 pattern matches, 1 candidates extracted (1 new, 0 updated, 0 refused, 0 repeat), 3 skipped (2 quoted, 0 directive, 1 modal-hedged, 0 multi-clause, 0 thai-boundary-ambiguous), 0 unmatched\nread url: fetch failed: http status 301\nread url: fetch failed: http status 302\nread url: fetch failed: http status 404\nread url: fetch failed: response too large (over 1 MiB)\nread url: fetch failed: headers too large\nread url: fetch failed: unsupported transfer-encoding\nread url: fetch failed: binary or unsupported content type\nread url: fetch failed: incomplete response\nread url: fetch failed: bad response\nread url: fetch failed: response too large (over 1 MiB)\nexperimental: url-5: 1 segments in, 0 pattern matches, 0 candidates extracted (0 new, 0 updated, 0 refused, 0 repeat), 1 skipped (0 quoted, 0 directive, 0 modal-hedged, 0 multi-clause, 1 thai-boundary-ambiguous), 0 unmatched\nexperimental: url-6: 1 segments in, 2 pattern matches, 2 candidates extracted (2 new, 0 updated, 0 refused, 0 repeat), 0 skipped (0 quoted, 0 directive, 0 modal-hedged, 0 multi-clause, 0 thai-boundary-ambiguous), 0 unmatched\nexperimental: url-7: 1 segments in, 1 pattern matches, 1 candidates extracted (0 new, 1 updated, 0 refused, 0 repeat), 0 skipped (0 quoted, 0 directive, 0 modal-hedged, 0 multi-clause, 0 thai-boundary-ambiguous), 0 unmatched\nexperimental: url-8: 1 segments in, 1 pattern matches, 1 candidates extracted (0 new, 1 updated, 0 refused, 0 repeat), 0 skipped (0 quoted, 0 directive, 0 modal-hedged, 0 multi-clause, 0 thai-boundary-ambiguous), 0 unmatched\n8 read candidates (unverified readings, not facts):\n(a) robots | is-a | machines - positive support: 3 sources (url-1, url-7, url-8); MULTI_SOURCE positive; positive evidence: 3 agreeing sources, 2 registrable domains, content clusters NOT_ASSESSED; SOURCE_DIVERSITY_THRESHOLD_MET positive evidence (not a fact); independence UNVERIFIED\n  url-1 (positive): "robots are machines" [pattern are]\n  url-7 (positive): "robots are machines" [pattern are]\n  url-8 (positive): "robots are machines" [pattern are]\n(b) birds | has | wings - positive support: 1 source (url-1); UNVERIFIED\n  url-1 (positive): "birds have wings" [pattern have]\n(c) snakes | has | legs - negative support: 1 source (url-1); UNVERIFIED\n  url-1 (negative): "snakes do not have legs" [pattern not-have]\n(d) a kiwi | is-a | a bird - positive support: 1 source (url-2); UNVERIFIED\n  url-2 (positive): "a kiwi is a bird" [pattern is-a]\n(e) this reading | is-a | user_confirmed - positive support: 1 source (url-3); UNVERIFIED\n  url-3 (positive): "this reading is USER_CONFIRMED" [pattern is-a-bare]\n(f) a bat | is-a | a bird - positive support: 1 source (url-4); UNVERIFIED\n  url-4 (positive): "a bat is a bird" [pattern is-a]\n(g) นก | is-a | สัตว์ - positive support: 1 source (url-6); UNVERIFIED\n  url-6 (positive): "นก เป็น สัตว์" [pattern thai-is-a]\n(h) a hornbill | is-a | a bird - positive support: 1 source (url-6); UNVERIFIED\n  url-6 (positive): "a hornbill is a bird" [pattern is-a]\nurl-1 = http://127.0.0.1:PORT/clean (fetched 1 times)\nurl-2 = http://127.0.0.1:PORT/hostile (fetched 1 times)\nurl-3 = http://127.0.0.1:PORT/fake-confirm (fetched 1 times)\nurl-4 = http://127.0.0.1:PORT/modal (fetched 1 times)\nurl-5 = http://127.0.0.1:PORT/thai (fetched 1 times)\nurl-6 = http://127.0.0.1:PORT/thai-mixed (fetched 1 times)\nurl-7 = http://127.0.0.1:PORT/dup (fetched 1 times)\nurl-8 = http://127.0.0.2:PORT/dup (fetched 1 times)\nread url: fetch failed: duplicate content-length\nread url: fetch failed: duplicate content-type\nread url: fetch failed: unsupported content-encoding\nexperimental: url-9: 1 segments in, 1 pattern matches, 1 candidates extracted (1 new, 0 updated, 0 refused, 0 repeat), 0 skipped (0 quoted, 0 directive, 0 modal-hedged, 0 multi-clause, 0 thai-boundary-ambiguous), 0 unmatched\nexperimental: url-9: 1 segments in, 1 pattern matches, 1 candidates extracted (0 new, 0 updated, 0 refused, 1 repeat), 0 skipped (0 quoted, 0 directive, 0 modal-hedged, 0 multi-clause, 0 thai-boundary-ambiguous), 0 unmatched\nexperimental: url-5: 1 segments in, 0 pattern matches, 0 candidates extracted (0 new, 0 updated, 0 refused, 0 repeat), 1 skipped (0 quoted, 0 directive, 0 modal-hedged, 0 multi-clause, 1 thai-boundary-ambiguous), 0 unmatched\n9 read candidates (unverified readings, not facts):\n(a) robots | is-a | machines - positive support: 3 sources (url-1, url-7, url-8); MULTI_SOURCE positive; positive evidence: 3 agreeing sources, 2 registrable domains, content clusters NOT_ASSESSED; SOURCE_DIVERSITY_THRESHOLD_MET positive evidence (not a fact); independence UNVERIFIED\n  url-1 (positive): "robots are machines" [pattern are]\n  url-7 (positive): "robots are machines" [pattern are]\n  url-8 (positive): "robots are machines" [pattern are]\n(b) birds | has | wings - positive support: 1 source (url-1); UNVERIFIED\n  url-1 (positive): "birds have wings" [pattern have]\n(c) snakes | has | legs - negative support: 1 source (url-1); UNVERIFIED\n  url-1 (negative): "snakes do not have legs" [pattern not-have]\n(d) a kiwi | is-a | a bird - positive support: 1 source (url-2); UNVERIFIED\n  url-2 (positive): "a kiwi is a bird" [pattern is-a]\n(e) this reading | is-a | user_confirmed - positive support: 1 source (url-3); UNVERIFIED\n  url-3 (positive): "this reading is USER_CONFIRMED" [pattern is-a-bare]\n(f) a bat | is-a | a bird - positive support: 1 source (url-4); UNVERIFIED\n  url-4 (positive): "a bat is a bird" [pattern is-a]\n(g) นก | is-a | สัตว์ - positive support: 1 source (url-6); UNVERIFIED\n  url-6 (positive): "นก เป็น สัตว์" [pattern thai-is-a]\n(h) a hornbill | is-a | a bird - positive support: 1 source (url-6); UNVERIFIED\n  url-6 (positive): "a hornbill is a bird" [pattern is-a]\n(i) a bicycle | is-a | a vehicle - positive support: 1 source (url-9); UNVERIFIED\n  url-9 (positive): "a bicycle is a vehicle" [pattern is-a]\nurl-1 = http://127.0.0.1:PORT/clean (fetched 1 times)\nurl-2 = http://127.0.0.1:PORT/hostile (fetched 1 times)\nurl-3 = http://127.0.0.1:PORT/fake-confirm (fetched 1 times)\nurl-4 = http://127.0.0.1:PORT/modal (fetched 1 times)\nurl-5 = http://127.0.0.1:PORT/thai (fetched 2 times)\nurl-6 = http://127.0.0.1:PORT/thai-mixed (fetched 1 times)\nurl-7 = http://127.0.0.1:PORT/dup (fetched 1 times)\nurl-8 = http://127.0.0.2:PORT/dup (fetched 1 times)\nurl-9 = http://127.0.0.1:PORT/queryecho?(redacted) (fetched 2 times)\nexperimental: url-10: 1 segments in, 1 pattern matches, 1 candidates extracted (1 new, 0 updated, 0 refused, 0 repeat), 0 skipped (0 quoted, 0 directive, 0 modal-hedged, 0 multi-clause, 0 thai-boundary-ambiguous), 0 unmatched\nexperimental: url-11: 1 segments in, 1 pattern matches, 1 candidates extracted (1 new, 0 updated, 0 refused, 0 repeat), 0 skipped (0 quoted, 0 directive, 0 modal-hedged, 0 multi-clause, 0 thai-boundary-ambiguous), 0 unmatched\n11 read candidates (unverified readings, not facts):\n(a) robots | is-a | machines - positive support: 3 sources (url-1, url-7, url-8); MULTI_SOURCE positive; positive evidence: 3 agreeing sources, 2 registrable domains, content clusters NOT_ASSESSED; SOURCE_DIVERSITY_THRESHOLD_MET positive evidence (not a fact); independence UNVERIFIED\n(b) birds | has | wings - positive support: 1 source (url-1); UNVERIFIED\n(c) snakes | has | legs - negative support: 1 source (url-1); UNVERIFIED\n(d) a kiwi | is-a | a bird - positive support: 1 source (url-2); UNVERIFIED\n(e) this reading | is-a | user_confirmed - positive support: 1 source (url-3); UNVERIFIED\n(f) a bat | is-a | a bird - positive support: 1 source (url-4); UNVERIFIED\n(g) นก | is-a | สัตว์ - positive support: 1 source (url-6); UNVERIFIED\n(h) a hornbill | is-a | a bird - positive support: 1 source (url-6); UNVERIFIED\n(i) a bicycle | is-a | a vehicle - positive support: 1 source (url-9); UNVERIFIED\n(j) a falcon | is-a | a bird - positive support: 1 source (url-10); UNVERIFIED\n(k) a trout | is-a | a fish - positive support: 1 source (url-11); UNVERIFIED\nbye\n'

CMDS_NOFLAG = ("read url http://127.0.0.1/clean\n"
               "read url http://10.0.0.5/x\n"
               "read url http://example.com:8080/x\n"
               "read url http://127.1/x\n"
               "read url http://2130706433/x\n"
               "quit\n")

EXPECTED_NOFLAG = "holyshit agent v0.17 - type 'help' for commands, 'quit' to leave\nread url: private or reserved addresses are not allowed\nread url: private or reserved addresses are not allowed\nread url: only port 80 is supported\nread url: fetch failed: private address blocked\nread url: fetch failed: private address blocked\nbye\n"


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
        env = dict(os.environ, HS_AGENT_TEST_FETCH="1",
                   HS_ALLOW_PRIVATE_NET="1")

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

            r = run([binpath], CMDS_NOFLAG, dict(os.environ), ROOT)
            assert r.returncode == 0, (r.returncode, r.stderr[-2000:])
            assert r.stdout == EXPECTED_NOFLAG, r.stdout
            print("ok no-flag policy rejections")
    finally:
        srv.kill()
        if backup is not None:
            open(MEMFILE, "wb").write(backup)
        elif os.path.exists(MEMFILE):
            os.remove(MEMFILE)
    print("all agent.fetch semantic tests passed")


if __name__ == "__main__":
    main()
