#!/usr/bin/env python3
"""Native LSP differential: python3 tests/test_lsp_native.py
Builds selfhost/lsp.holy with xbuild and runs the same stdio scenario against
it and lsp.py, requiring identical responses and publishDiagnostics streams
(initialize/sync/diagnostics/shutdown; L1 protocol core).
"""
import json
import os
import select
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

fails = 0
total = 0


def check(name, cond, detail=""):
    global fails, total
    total += 1
    if cond:
        print(f"ok   {name}")
    else:
        print(f"FAIL {name} {detail}")
        fails += 1


class Client:
    def __init__(self, argv, env=None):
        self.p = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=env)
        self.seq = 0
        self.diags = []
        self.responses = []

    def read_msg(self):
        length = 0
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise EOFError("closed")
            s = line.strip()
            if not s:
                break
            if s.lower().startswith(b"content-length:"):
                length = int(s.split(b":", 1)[1])
        body = b""
        while len(body) < length:
            chunk = self.p.stdout.read(length - len(body))
            if not chunk:
                raise EOFError("short")
            body += chunk
        return json.loads(body.decode("utf-8"))

    def _write(self, msg):
        body = json.dumps(msg).encode()
        self.p.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        self.p.stdin.flush()

    def request(self, method, params):
        self.seq += 1
        mid = self.seq
        self._write({"jsonrpc": "2.0", "id": mid, "method": method,
                     "params": params})
        while True:
            m = self.read_msg()
            if m.get("method") == "textDocument/publishDiagnostics":
                self.diags.append(m["params"])
                continue
            if m.get("id") == mid:
                self.responses.append(m)
                return m

    def notify(self, method, params):
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def drain(self, timeout=0.5):
        while True:
            r, _, _ = select.select([self.p.stdout], [], [], timeout)
            if not r:
                break
            m = self.read_msg()
            if m.get("method") == "textDocument/publishDiagnostics":
                self.diags.append(m["params"])
            else:
                self.responses.append(m)


GOOD = "x = 1\ny = x + 2\nprint y\n"
PARSE_ERR = "def f(:\n  pass\n"
PARSE_ERR2 = "x = 1\nif x\n  print x\n"
SEM_ERR = "print undefined_name_xyz\n"
SEM_ERR2 = "def f():\n  return missing_thing + 1\nf()\n"
NONASCII = "name = \"caf\u00e9 \u4e2d\u6587\"\nprint missing_after_unicode\n"
UNCLOSED = "xs = [1, 2\n"


def scenario(argv, env=None):
    """One fixed message sequence; returns the comparable server output."""
    c = Client(argv, env)
    out = {}
    out["init"] = c.request("initialize", {
        "processId": None, "rootPath": "/tmp", "capabilities": {}})
    c.notify("initialized", {})
    uri = "file:///tmp/lsp_native_probe.holy"

    def open_doc(text, tag):
        c.diags.clear()
        c.notify("textDocument/didOpen", {"textDocument": {
            "uri": uri, "languageId": "holyshit", "version": 1,
            "text": text}})
        c.drain()
        out[tag] = list(c.diags)

    open_doc(GOOD, "open_good")
    open_doc(PARSE_ERR, "open_parse_err")
    open_doc(PARSE_ERR2, "open_parse_err2")
    open_doc(SEM_ERR, "open_sem_err")
    open_doc(SEM_ERR2, "open_sem_err2")
    open_doc(NONASCII, "open_nonascii")
    open_doc(UNCLOSED, "open_unclosed")
    open_doc("", "open_empty")

    # didChange transitions: clean -> parse error -> semantic error -> clean
    for tag, text in [("ch_clean", GOOD), ("ch_parse", PARSE_ERR),
                      ("ch_sem", SEM_ERR), ("ch_back", GOOD)]:
        c.diags.clear()
        c.notify("textDocument/didChange", {
            "textDocument": {"uri": uri, "version": 2},
            "contentChanges": [{"text": text}]})
        c.drain()
        out[tag] = list(c.diags)

    # didSave with and without text
    c.diags.clear()
    c.notify("textDocument/didSave", {
        "textDocument": {"uri": uri, "version": 3}, "text": SEM_ERR})
    c.drain()
    out["save_text"] = list(c.diags)
    c.diags.clear()
    c.notify("textDocument/didSave", {"textDocument": {"uri": uri}})
    c.drain()
    out["save_notext"] = list(c.diags)

    # didClose: silent, and a later reopen diagnoses afresh
    c.diags.clear()
    c.notify("textDocument/didClose", {"textDocument": {"uri": uri}})
    c.drain()
    out["close"] = list(c.diags)
    open_doc(PARSE_ERR, "reopen_parse_err")

    out["unknown"] = c.request("workspace/doesNotExist", {})
    out["shutdown"] = c.request("shutdown", None)
    c.notify("exit", {})
    c.p.wait(timeout=10)
    out["exitcode"] = c.p.returncode
    return out


def pipelined(argv, env=None):
    """Three messages in ONE write: byte-exact framing must not over-read."""
    c = Client(argv, env)
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"processId": None, "rootPath": "/tmp", "capabilities": {}}},
        {"jsonrpc": "2.0", "method": "textDocument/didOpen",
         "params": {"textDocument": {"uri": "file:///tmp/pipe.holy",
                                     "languageId": "holyshit", "version": 1,
                                     "text": PARSE_ERR}}},
        {"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": None},
    ]
    blob = b""
    for m in msgs:
        body = json.dumps(m).encode()
        blob += b"Content-Length: %d\r\n\r\n" % len(body) + body
    c.p.stdin.write(blob)
    c.p.stdin.flush()
    got_init = got_diag = got_shutdown = None
    for _ in range(3):
        m = c.read_msg()
        if m.get("id") == 1:
            got_init = m
        elif m.get("id") == 2:
            got_shutdown = m
        elif m.get("method") == "textDocument/publishDiagnostics":
            got_diag = m
    c.p.stdin.close()
    c.p.wait(timeout=10)
    return got_init, got_diag, got_shutdown, c.p.returncode


def main():
    with tempfile.TemporaryDirectory() as td:
        exe = os.path.join(td, "hs_lsp_native")
        env = dict(os.environ)
        env["HSPATH"] = os.path.join(ROOT, "selfhost") + os.pathsep + \
            os.path.join(ROOT, "selfhost", "be")
        env["HSROOT"] = ROOT
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "hs.py"), "xbuild",
             os.path.join(ROOT, "selfhost", "lsp.holy"), "-o", exe],
            capture_output=True, text=True, env=env)
        check("native lsp builds", r.returncode == 0 and os.path.exists(exe),
              (r.stdout + r.stderr)[-200:])
        if r.returncode != 0 or not os.path.exists(exe):
            print(f"{total - fails}/{total} passed")
            sys.exit(1)

        py = scenario([sys.executable, os.path.join(ROOT, "lsp.py")])
        hs = scenario([exe])
        for k in py:
            check(f"scenario {k}", py[k] == hs[k],
                  f"\n  py: {json.dumps(py[k])[:300]}"
                  f"\n  hs: {json.dumps(hs[k])[:300]}")

        pin = py["init"]["result"]
        check("initialize capabilities shape",
              pin["capabilities"]["textDocumentSync"] == 1
              and pin["serverInfo"] == {"name": "holyshit-lsp",
                                        "version": "0.6.0"})
        check("parse-error diagnostic shape",
              hs["open_parse_err"][0]["diagnostics"][0]["severity"] == 1
              and hs["open_parse_err"][0]["diagnostics"][0]["source"] == "hs")

        pp = pipelined([sys.executable, os.path.join(ROOT, "lsp.py")])
        hh = pipelined([exe])
        check("pipelined messages", pp == hh,
              f"\n  py: {json.dumps([x if not isinstance(x, dict) else x for x in pp], default=str)[:300]}"
              f"\n  hs: {json.dumps([x if not isinstance(x, dict) else x for x in hh], default=str)[:300]}")

    print(f"{total - fails}/{total} native lsp differential gates")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
