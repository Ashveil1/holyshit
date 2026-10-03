#!/usr/bin/env python3
"""One-shot LSP client for holyshit — usable by any agent in one command.

    python3 scripts/lsp_client.py --diag prog.hs
    python3 scripts/lsp_client.py --hover prog.hs 3 5
    python3 scripts/lsp_client.py --complete prog.hs 1 4
    python3 scripts/lsp_client.py --def prog.hs 2 10
    python3 scripts/lsp_client.py --symbols prog.hs
    python3 scripts/lsp_client.py --format prog.hs [--write]
    Lines/cols are 1-based for humans; converted to LSP 0-based here.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Client:
    def __init__(self):
        self.p = subprocess.Popen(
            [sys.executable, os.path.join(ROOT, "lsp.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL)
        self.seq = 0
        self.pending_diags = []

    def send(self, obj):
        body = json.dumps(obj).encode("utf-8")
        self.p.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        self.p.stdin.flush()

    def read_msg(self):
        length = 0
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise EOFError("lsp server closed stdout")
            line = line.strip()
            if not line:
                break
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":", 1)[1])
        if not length:
            return self.read_msg()
        body = b""
        while len(body) < length:
            chunk = self.p.stdout.read(length - len(body))
            if not chunk:
                raise EOFError("short read")
            body += chunk
        return json.loads(body.decode("utf-8"))

    def request(self, method, params):
        self.seq += 1
        mid = self.seq
        self.send({"jsonrpc": "2.0", "id": mid, "method": method,
                   "params": params})
        while True:
            msg = self.read_msg()
            if "id" in msg and msg["id"] == mid:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result")
            if msg.get("method") == "textDocument/publishDiagnostics":
                self.pending_diags.append(msg["params"])

    def notify(self, method, params):
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def open(self, path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        uri = "file://" + os.path.abspath(path)
        self.request("initialize", {"rootUri": None, "capabilities": {}})
        self.notify("initialized", {})
        self.notify("textDocument/didOpen",
                    {"textDocument": {"uri": uri, "languageId": "holyshit",
                                      "text": text, "version": 1}})
        return uri

    def close(self):
        try:
            self.request("shutdown", {})
        except Exception:
            pass
        try:
            self.notify("exit", {})
            self.p.stdin.close()
        except BrokenPipeError:
            pass
        self.p.wait(timeout=10)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    mode, path = argv[1], argv[2]
    c = Client()
    try:
        uri = c.open(path)
        if mode == "--diag":
            c.request("textDocument/documentSymbol",
                      {"textDocument": {"uri": uri}})  # flush round-trip
            print(json.dumps(c.pending_diags, indent=1))
        elif mode == "--hover":
            ln, col = int(argv[3]) - 1, int(argv[4]) - 1
            print(json.dumps(c.request(
                "textDocument/hover",
                {"textDocument": {"uri": uri},
                 "position": {"line": ln, "character": col}}), indent=1))
        elif mode == "--complete":
            ln, col = int(argv[3]) - 1, int(argv[4]) - 1
            r = c.request("textDocument/completion",
                          {"textDocument": {"uri": uri},
                           "position": {"line": ln, "character": col}})
            print(json.dumps([i["label"] for i in r["items"]]))
        elif mode == "--def":
            ln, col = int(argv[3]) - 1, int(argv[4]) - 1
            print(json.dumps(c.request(
                "textDocument/definition",
                {"textDocument": {"uri": uri},
                 "position": {"line": ln, "character": col}}), indent=1))
        elif mode == "--symbols":
            print(json.dumps(c.request(
                "textDocument/documentSymbol",
                {"textDocument": {"uri": uri}}), indent=1))
        elif mode == "--format":
            r = c.request("textDocument/formatting",
                          {"textDocument": {"uri": uri},
                           "options": {"tabSize": 2, "insertSpaces": True}})
            if "--write" in argv and r:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(r[0]["newText"])
                print("formatted")
            else:
                print(json.dumps(r, indent=1)[:2000])
        else:
            print(__doc__)
            return 2
    finally:
        c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
