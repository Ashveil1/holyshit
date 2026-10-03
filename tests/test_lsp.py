#!/usr/bin/env python3
"""LSP protocol tests: python3 tests/test_lsp.py
Spawns lsp.py over stdio and checks initialize/diagnostics/hover/
completion/definition/symbols/formatting, incl. cross-file definition.
"""
import json
import os
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
    def __init__(self):
        self.p = subprocess.Popen(
            [sys.executable, os.path.join(ROOT, "lsp.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL)
        self.seq = 0
        self.diags = []

    def read_msg(self):
        length = 0
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise EOFError("closed")
            line = line.strip()
            if not line:
                break
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":", 1)[1])
        body = b""
        while len(body) < length:
            chunk = self.p.stdout.read(length - len(body))
            if not chunk:
                raise EOFError("short")
            body += chunk
        return json.loads(body.decode("utf-8"))

    def request(self, method, params):
        self.seq += 1
        mid = self.seq
        body = json.dumps({"jsonrpc": "2.0", "id": mid, "method": method,
                           "params": params}).encode()
        self.p.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        self.p.stdin.flush()
        while True:
            msg = self.read_msg()
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result")
            if msg.get("method") == "textDocument/publishDiagnostics":
                self.diags.append(msg["params"])

    def notify(self, method, params):
        body = json.dumps({"jsonrpc": "2.0", "method": method,
                           "params": params}).encode()
        self.p.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        self.p.stdin.flush()

    def open(self, path, text):
        uri = "file://" + path
        self.request("initialize", {"capabilities": {}})
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


with tempfile.TemporaryDirectory() as d:
    # 1. diagnostics: broken file reports the parse error line
    c = Client()
    bad = os.path.join(d, "bad.hs")
    with open(bad, "w") as f:
        f.write('print 1 +\n')
    uri = c.open(bad, 'print 1 +\n')
    c.request("textDocument/documentSymbol",
              {"textDocument": {"uri": uri}})  # round-trip flush
    msgs = [x["message"] for p in c.diags for x in p["diagnostics"]]
    check("diag parse error", any("expression expected" in m for m in msgs),
          msgs)
    ln = [x["range"]["start"]["line"] for p in c.diags
          for x in p["diagnostics"]]
    check("diag line 0-based", ln == [0], ln)
    c.close()

    # 2. clean file: no diagnostics
    c = Client()
    good = os.path.join(d, "good.hs")
    src = 'def add(a, b):\n  return a + b\n\nprint add(1, 2)\n'
    with open(good, "w") as f:
        f.write(src)
    uri = c.open(good, src)
    c.request("textDocument/documentSymbol",
              {"textDocument": {"uri": uri}})
    check("diag clean", c.diags and all(
        len(p["diagnostics"]) == 0 for p in c.diags), c.diags)

    # 3. hover on user function + builtin
    h = c.request("textDocument/hover",
                  {"textDocument": {"uri": uri},
                   "position": {"line": 3, "character": 6}})
    check("hover user func", h and "def add(a, b)" in
          h["contents"]["value"], h)
    c2uri = uri
    with open(os.path.join(d, "b2.hs"), "w") as f:
        f.write('print len("hi")\n')
    c.notify("textDocument/didOpen",
             {"textDocument": {"uri": "file://" + os.path.join(d, "b2.hs"),
                               "languageId": "holyshit",
                               "text": 'print len("hi")\n', "version": 1}})
    h = c.request("textDocument/hover",
                  {"textDocument": {"uri": "file://" + os.path.join(d, "b2.hs")},
                   "position": {"line": 0, "character": 7}})
    check("hover builtin", h and "len(x)" in h["contents"]["value"], h)

    # 4. definition in same file (call -> def line 0)
    loc = c.request("textDocument/definition",
                    {"textDocument": {"uri": c2uri},
                     "position": {"line": 3, "character": 6}})
    check("definition same file",
          loc and loc["uri"] == c2uri and loc["range"]["start"]["line"] == 0,
          loc)

    # 5. completion contains keywords + builtins + user symbols
    r = c.request("textDocument/completion",
                  {"textDocument": {"uri": c2uri},
                   "position": {"line": 3, "character": 2}})
    labels = [i["label"] for i in r["items"]]
    check("completion mixed", "while" in labels and "print" in labels
          and "add" in labels, labels[:5])

    # 6. document symbols
    syms = c.request("textDocument/documentSymbol",
                     {"textDocument": {"uri": c2uri}})
    names = [s["name"] for s in syms]
    check("symbols", "add" in names and "a" in names, names)
    c.close()

    # 7. cross-file: mod.attr jumps into the module file
    mdir = os.path.join(d, "pkg")
    os.mkdir(mdir)
    with open(os.path.join(mdir, "mymod.hs"), "w") as f:
        f.write("def double(x):\n  return x * 2\n")
    main = os.path.join(mdir, "main.hs")
    msrc = "import mymod\n\nprint mymod.double(2)\n"
    with open(main, "w") as f:
        f.write(msrc)
    c = Client()
    uri = c.open(main, msrc)
    loc = c.request("textDocument/definition",
                    {"textDocument": {"uri": uri},
                     "position": {"line": 2, "character": 14}})
    check("definition cross-file",
          loc and loc["uri"].endswith("mymod.hs")
          and loc["range"]["start"]["line"] == 0, loc)
    loc = c.request("textDocument/definition",
                    {"textDocument": {"uri": uri},
                     "position": {"line": 0, "character": 8}})
    check("definition import->file",
          loc and loc["uri"].endswith("mymod.hs"), loc)
    c.close()

    # 8. formatting canonicalizes
    c = Client()
    ugly = os.path.join(d, "ugly.hs")
    with open(ugly, "w") as f:
        f.write("def  add( a,b ):\n    return a+b\n")
    uri = c.open(ugly, "def  add( a,b ):\n    return a+b\n")
    r = c.request("textDocument/formatting",
                  {"textDocument": {"uri": uri},
                   "options": {"tabSize": 2, "insertSpaces": True}})
    check("formatting", r and r[0]["newText"] == "def add(a, b):\n  return a + b\n",
          r)
    c.close()

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
