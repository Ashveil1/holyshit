#!/usr/bin/env python3
"""Outbound network policy: connect-time private-network guard (R1) and
bounded receive timeouts (R2), identical on the interp and native routes.

Guard legs (no HS_ALLOW_PRIVATE_NET): literal loopback/private/link-local/
unspecified/multicast destinations, IPv4 and IPv6 (incl v4-mapped), and a
hostname resolving to a loopback answer must all fail with the stable error
'connect blocked: private address'. Timeout legs (HS_ALLOW_PRIVATE_NET=1,
fixture servers on 127.0.0.1): fast fetch succeeds; silent peer -> 'idle
timeout'; slow drip -> 'deadline exceeded'; premature close with
Content-Length -> 'http_get incomplete response'; a 1 MiB fast response
succeeds (timeouts must not break the fast path). Unit legs exercise the
interp resolver hook directly: a hostname with mixed public+private answers
fails closed, and the connect targets the exact checked address (no second
resolution between check and connect).

Bare IPv6-literal URLs are rejected by the http:// parser on both routes
(pre-existing); v6 guard coverage runs through tcp_connect, which takes the
address verbatim.

--skip-native skips the native legs (sandbox without Boehm GC).
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HS = [sys.executable, str(ROOT / "hs.py")]

passed = failed = 0
notes = []


def ok(name, detail=""):
    global passed
    passed += 1
    print(f"ok   {name} {detail}".rstrip())


def bad(name, detail=""):
    global failed
    failed += 1
    print(f"FAIL {name} {detail}".rstrip())


def serve(handler, ready=None):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]

    def run():
        try:
            c, _ = srv.accept()
            try:
                handler(c)
            finally:
                c.close()
        except OSError:
            pass
        finally:
            srv.close()

    threading.Thread(target=run, daemon=True).start()
    return port


def h_fast(c):
    c.recv(65536)
    c.sendall(b"HTTP/1.0 200 OK\r\nContent-Length: 5\r\n\r\nhello")
    c.shutdown(socket.SHUT_WR)
    while c.recv(65536):
        pass


def h_silent(c):
    c.recv(65536)
    time.sleep(45)


def h_partial_stall(c):
    c.recv(65536)
    c.sendall(b"HTTP/1.0 200 OK\r\nContent-Length: 100\r\n\r\n")
    time.sleep(45)


def h_drip(c):
    c.recv(65536)
    c.sendall(b"HTTP/1.0 200 OK\r\n\r\n")
    for _ in range(45):
        try:
            c.sendall(b"x")
        except OSError:
            break
        time.sleep(1)


def h_premature(c):
    c.recv(65536)
    c.sendall(b"HTTP/1.0 200 OK\r\nContent-Length: 100\r\n\r\nshort")
    c.shutdown(socket.SHUT_WR)
    while c.recv(65536):
        pass


def h_large(c):
    c.recv(65536)
    body = b"y" * (1 << 20)
    c.sendall(b"HTTP/1.0 200 OK\r\nContent-Length: %d\r\n\r\n" % len(body) + body)
    c.shutdown(socket.SHUT_WR)
    while c.recv(65536):
        pass


def run_hs(route, src, args, env_extra, timeout):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "prog.holy"
        f.write_text(src)
        env = dict(os.environ, HSPATH=str(ROOT / "selfhost") + ":" + str(ROOT / "selfhost" / "be"),
                   HSROOT=str(ROOT))
        env.update(env_extra)
        if route == "interp":
            cmd = HS + ["run", str(f)] + args
        else:
            exe = str(Path(d) / "prog")
            b = subprocess.run(HS + ["build", str(f), "-o", exe], capture_output=True, text=True)
            if b.returncode != 0:
                return -2, b.stderr.strip().splitlines()[-1] if b.stderr.strip() else "build failed"
            cmd = [exe] + args
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            return -3, f"hung past {timeout}s"
        return r.returncode, (r.stdout + r.stderr).strip(), time.time() - t0


HTTP_SRC = 'b = http_get(argv()[0])\nprint(byte_len(b))\n'
RECV_SRC = 's = tcp_connect(argv()[0], int(argv()[1]))\nd = tcp_recv(s, 100)\nprint(byte_len(d))\n'
CONN_SRC = 's = tcp_connect(argv()[0], int(argv()[1]))\nprint("CONNECTED")\n'

ALLOW = {"HS_ALLOW_PRIVATE_NET": "1"}

GUARD_HOSTS = [
    ("127.0.0.1", "loopback"),
    ("10.1.2.3", "private 10/8"),
    ("172.16.5.5", "private 172.16/12"),
    ("172.31.255.255", "private 172.31/12 edge"),
    ("192.168.0.1", "private 192.168/16"),
    ("169.254.169.254", "link-local cloud metadata"),
    ("0.0.0.0", "unspecified"),
    ("224.0.0.1", "multicast"),
    ("localhost", "hostname resolving to loopback"),
]
GUARD_HOSTS_V6 = [
    ("::1", "v6 loopback"),
    ("::ffff:127.0.0.1", "v4-mapped v6 loopback"),
    ("fe80::1", "v6 link-local"),
    ("fc00::1", "v6 unique-local"),
]


def leg_guard(route):
    for host, why in GUARD_HOSTS:
        rc, out, _ = run_hs(route, HTTP_SRC, [f"http://{host}/"], {}, 40)
        if rc != 0 and "connect blocked: private address" in out:
            ok(f"{route} guard http v4", why)
        else:
            bad(f"{route} guard http v4", f"{why}: rc={rc} out={out!r}")
    for host, why in GUARD_HOSTS_V6:
        rc, out, _ = run_hs(route, CONN_SRC, [host, "80"], {}, 40)
        if rc != 0 and "connect blocked: private address" in out:
            ok(f"{route} guard tcp v6", why)
        else:
            bad(f"{route} guard tcp v6", f"{why}: rc={rc} out={out!r}")


def leg_fetch(route):
    port = serve(h_fast)
    rc, out, _ = run_hs(route, HTTP_SRC, [f"http://127.0.0.1:{port}/"], ALLOW, 40)
    if rc == 0 and "5" in out:
        ok(f"{route} fetch fast fixture")
    else:
        bad(f"{route} fetch fast fixture", f"rc={rc} out={out!r}")

    port = serve(h_silent)
    rc, out, dt = run_hs(route, HTTP_SRC, [http := f"http://127.0.0.1:{port}/"], ALLOW, 45)
    if rc != 0 and "idle timeout" in out and dt < 30:
        ok(f"{route} fetch no-response idle timeout", f"{dt:.1f}s")
    else:
        bad(f"{route} fetch no-response idle timeout", f"rc={rc} {dt:.1f}s out={out!r}")

    port = serve(h_partial_stall)
    rc, out, dt = run_hs(route, HTTP_SRC, [f"http://127.0.0.1:{port}/"], ALLOW, 45)
    if rc != 0 and "idle timeout" in out and dt < 30:
        ok(f"{route} fetch partial-stall idle timeout", f"{dt:.1f}s")
    else:
        bad(f"{route} fetch partial-stall idle timeout", f"rc={rc} {dt:.1f}s out={out!r}")

    port = serve(h_drip)
    rc, out, dt = run_hs(route, HTTP_SRC, [f"http://127.0.0.1:{port}/"], ALLOW, 60)
    if rc != 0 and "deadline exceeded" in out:
        ok(f"{route} fetch slow-drip deadline", f"{dt:.1f}s")
    else:
        bad(f"{route} fetch slow-drip deadline", f"rc={rc} {dt:.1f}s out={out!r}")

    port = serve(h_premature)
    rc, out, _ = run_hs(route, HTTP_SRC, [f"http://127.0.0.1:{port}/"], ALLOW, 40)
    if rc != 0 and "incomplete response" in out:
        ok(f"{route} fetch premature-close incomplete")
    else:
        bad(f"{route} fetch premature-close incomplete", f"rc={rc} out={out!r}")

    port = serve(h_large)
    rc, out, _ = run_hs(route, HTTP_SRC, [f"http://127.0.0.1:{port}/"], ALLOW, 40)
    if rc == 0 and "1048576" in out:
        ok(f"{route} fetch 1MiB fast path")
    else:
        bad(f"{route} fetch 1MiB fast path", f"rc={rc} out={out!r}")

    port = serve(h_silent)
    rc, out, dt = run_hs(route, RECV_SRC, ["127.0.0.1", str(port)], ALLOW, 45)
    if rc != 0 and "idle timeout" in out and dt < 30:
        ok(f"{route} raw tcp_recv idle timeout", f"{dt:.1f}s")
    else:
        bad(f"{route} raw tcp_recv idle timeout", f"rc={rc} {dt:.1f}s out={out!r}")


def leg_unit():
    """Interp resolver hook: mixed answers fail closed; connect targets the
    exact checked address (rebinding cannot slip a second resolution in)."""
    sys.path.insert(0, str(ROOT))
    import interp

    calls = {"n": 0}

    def fake_gai_mixed(host, port, fam, stype):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.9.9.9", port)),
        ]

    orig = socket.getaddrinfo
    socket.getaddrinfo = fake_gai_mixed
    try:
        try:
            interp._net_dial("mixed.example", 80, 1, "tcp_connect")
            bad("unit mixed answers fail closed", "no error raised")
        except interp.HSErr as e:
            if "connect blocked: private address" in str(e.msg):
                ok("unit mixed answers fail closed")
            else:
                bad("unit mixed answers fail closed", f"wrong error: {e.msg}")
    finally:
        socket.getaddrinfo = orig

    connected = []

    class FakeSock:
        def settimeout(self, t):
            pass

        def connect(self, sa):
            connected.append(sa)

        def close(self):
            pass

    def fake_gai_one(host, port, fam, stype):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    def fake_socket(fam, stype, proto):
        return FakeSock()

    orig_gai, orig_sock = socket.getaddrinfo, socket.socket
    socket.getaddrinfo = fake_gai_one
    socket.socket = fake_socket
    try:
        s = interp._net_dial("rebind.example", 80, 1, "tcp_connect")
        if connected == [("93.184.216.34", 80)]:
            ok("unit connect-to-checked-ip")
        else:
            bad("unit connect-to-checked-ip", f"connected={connected!r}")
    except interp.HSErr as e:
        bad("unit connect-to-checked-ip", f"raised: {e.msg}")
    finally:
        socket.getaddrinfo = orig_gai
        socket.socket = orig_sock


def have_native():
    if shutil.which("gcc") is None:
        return False
    r = subprocess.run(["gcc", "-fsyntax-only", "-x", "c", "-"],
                       input="#include <gc.h>\n", text=True, capture_output=True)
    return r.returncode == 0


def main():
    leg_guard("interp")
    leg_fetch("interp")
    leg_unit()
    if "--skip-native" in sys.argv:
        notes.append("native legs skipped (--skip-native)")
    elif not have_native():
        notes.append("native legs skipped (no gcc + Boehm GC)")
    else:
        leg_guard("native")
        leg_fetch("native")
    for n in notes:
        print(f"note {n}")
    total = passed + failed
    if failed:
        print(f"{passed}/{total} netguard checks")
        return 1
    print(f"{passed}/{total} netguard checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
