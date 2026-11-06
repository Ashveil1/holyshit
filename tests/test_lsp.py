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
from pathlib import Path

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
        uri = Path(path).as_uri()
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
    bad = os.path.join(d, "bad.holy")
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
    good = os.path.join(d, "good.holy")
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
    with open(os.path.join(d, "b2.holy"), "w") as f:
        f.write('print len("hi")\n')
    c.notify("textDocument/didOpen",
             {"textDocument": {"uri": "file://" + os.path.join(d, "b2.holy"),
                               "languageId": "holyshit",
                               "text": 'print len("hi")\n', "version": 1}})
    h = c.request("textDocument/hover",
                  {"textDocument": {"uri": "file://" + os.path.join(d, "b2.holy")},
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
    with open(os.path.join(mdir, "mymod.holy"), "w") as f:
        f.write("def double(x):\n  return x * 2\n\nPI = 3\n")
    main = os.path.join(mdir, "main.holy")
    msrc = "import mymod\n\nprint mymod.double(2)\nprint mymod.PI\n"
    with open(main, "w") as f:
        f.write(msrc)
    c = Client()
    uri = c.open(main, msrc)
    loc = c.request("textDocument/definition",
                    {"textDocument": {"uri": uri},
                     "position": {"line": 2, "character": 14}})
    check("definition cross-file",
          loc and loc["uri"].endswith("mymod.holy")
          and loc["range"]["start"]["line"] == 0, loc)
    loc = c.request("textDocument/definition",
                    {"textDocument": {"uri": uri},
                     "position": {"line": 0, "character": 8}})
    check("definition import->file",
          loc and loc["uri"].endswith("mymod.holy"), loc)
    c.close()

    # 8. module members: hover + completion after "mymod."
    c = Client()
    uri = c.open(main, msrc)
    h = c.request("textDocument/hover",
                  {"textDocument": {"uri": uri},
                   "position": {"line": 2, "character": 8}})
    check("hover mod.attr function",
          h and "def double(x)" in h["contents"]["value"]
          and "mymod.holy" in h["contents"]["value"], h)
    h = c.request("textDocument/hover",
                  {"textDocument": {"uri": uri},
                   "position": {"line": 3, "character": 8}})
    check("hover mod.attr variable",
          h and "`PI`" in h["contents"]["value"], h)
    r = c.request("textDocument/completion",
                  {"textDocument": {"uri": uri},
                   "position": {"line": 2, "character": 7}})
    labels = [i["label"] for i in r["items"]]
    check("member completion", "double" in labels and "PI" in labels, labels)
    check("member completion excludes params", "x" not in labels, labels)
    c.close()

    # 9. references: same file + cross file, with declaration
    c = Client()
    rsrc = ("def add(a, b):\n  return a + b\n\n"
            "def twice(x):\n  return add(x, x)\n\nprint add(1, 2)\n")
    rpath = os.path.join(mdir, "refs.holy")
    with open(rpath, "w") as f:
        f.write(rsrc)
    uri = c.open(rpath, rsrc)
    refs = c.request("textDocument/references",
                     {"textDocument": {"uri": uri},
                      "position": {"line": 6, "character": 6},
                      "context": {"includeDeclaration": True}})
    lines = sorted(r["range"]["start"]["line"] for r in refs)
    check("references same file", lines == [0, 4, 6], lines)
    # references on mymod.double: declared in mymod.holy, used in main.holy
    refs = c.request("textDocument/references",
                     {"textDocument": {"uri": uri},
                      "position": {"line": 0, "character": 5},
                      "context": {"includeDeclaration": True}})
    check("references own declaration",
          any(r["uri"].endswith("refs.holy") and
              r["range"]["start"]["line"] == 0 for r in refs), refs)
    c.close()

    c = Client()
    uri = c.open(main, msrc)
    refs = c.request("textDocument/references",
                     {"textDocument": {"uri": uri},
                      "position": {"line": 2, "character": 8},
                      "context": {"includeDeclaration": True}})
    check("references cross file",
          any(r["uri"].endswith("main.holy") for r in refs)
          and any(r["uri"].endswith("mymod.holy") for r in refs), refs)
    c.close()

    # 10. document highlight: definition line + current line
    c = Client()
    uri = c.open(rpath, rsrc)
    hl = c.request("textDocument/documentHighlight",
                   {"textDocument": {"uri": uri},
                    "position": {"line": 4, "character": 10}})
    lines = sorted(h["range"]["start"]["line"] for h in hl)
    check("document highlight", lines == [0, 4], lines)
    kinds = {h["range"]["start"]["line"]: h["kind"] for h in hl}
    check("highlight marks definition read-only", kinds.get(0) == 1
          and kinds.get(4) == 2, kinds)
    c.close()

    # 11. signature help for builtin and user function
    c = Client()
    uri = c.open(rpath, rsrc)
    sig = c.request("textDocument/signatureHelp",
                    {"textDocument": {"uri": uri},
                     "position": {"line": 6, "character": 11}})
    labels = [s["label"] for s in sig["signatures"]]
    check("signature help user fn", "add(a, b)" in labels, labels)
    sig2 = c.request("textDocument/signatureHelp",
                     {"textDocument": {"uri": uri},
                      "position": {"line": 4, "character": 15}})
    check("signature help after comma",
          sig2 and sig2["signatures"][0]["activeParameter"] == 1, sig2)
    c.close()

    # 11b. signature help for a builtin
    c = Client()
    bsrc = "print range(10)\n"
    bpath = os.path.join(d, "bi.holy")
    with open(bpath, "w") as f:
        f.write(bsrc)
    uri = c.open(bpath, bsrc)
    sig = c.request("textDocument/signatureHelp",
                    {"textDocument": {"uri": uri},
                     "position": {"line": 0, "character": 12}})
    check("signature help builtin",
          sig and "range(n)" in sig["signatures"][0]["label"], sig)
    c.close()

    # 12. workspace symbols across the directory
    c = Client()
    uri = c.open(main, msrc)
    syms = c.request("workspace/symbol", {"query": "double"})
    files = {s["location"]["uri"].split("/")[-1] for s in syms}
    check("workspace symbol", files == {"mymod.holy"}, files)
    c.close()

    # 13. formatting canonicalizes
    c = Client()
    ugly = os.path.join(d, "ugly.holy")
    with open(ugly, "w") as f:
        f.write("def  add( a,b ):\n    return a+b\n")
    uri = c.open(ugly, "def  add( a,b ):\n    return a+b\n")
    r = c.request("textDocument/formatting",
                  {"textDocument": {"uri": uri},
                   "options": {"tabSize": 2, "insertSpaces": True}})
    check("formatting", r and r[0]["newText"] == "def add(a, b):\n  return a + b\n",
          r)
    c.close()

    # 14. didSave re-publishes diagnostics
    c = Client()
    with open(good, "w") as f:
        f.write(src)
    uri = c.open(good, src)
    c.diags.clear()
    c.notify("textDocument/didSave",
             {"textDocument": {"uri": uri}, "text": "print 1 +\n"})
    r = c.request("textDocument/documentSymbol",
                  {"textDocument": {"uri": uri}})
    msgs = [x["message"] for p in c.diags for x in p["diagnostics"]]
    check("didSave republishes diagnostics",
          any("expression expected" in m for m in msgs), msgs)
    c.close()

# Real editor URIs escape paths, unlike the old test client's raw concatenation.
# Keep literal percent-escapes in names to catch accidental double decoding.
for folder in ("with spaces", "hash#name", "percent%20name", "question?name", "ไทย😀"):
    with tempfile.TemporaryDirectory() as root:
        d = Path(root) / folder
        d.mkdir()
        mod = d / "mymod.holy"
        mod.write_text("def twice(x):\n  return x * 2\n", encoding="utf-8")
        main = d / "main.holy"
        src = "import mymod\nprint mymod.twice(4)\n"
        main.write_text(src, encoding="utf-8")
        c = Client()
        try:
            uri = c.open(str(main), src)
            params = {"textDocument": {"uri": uri},
                      "position": {"line": 1, "character": 15}}
            loc = c.request("textDocument/definition", params)
            check("encoded folder definition " + folder,
                  loc and loc["uri"] == mod.as_uri(), loc)
            refs = c.request("textDocument/references", dict(
                params, context={"includeDeclaration": True}))
            check("encoded folder references " + folder,
                  {r["uri"] for r in refs} == {main.as_uri(), mod.as_uri()}, refs)
            syms = c.request("workspace/symbol", {"query": "twice"})
            check("encoded folder workspace symbol " + folder,
                  len(syms) == 1 and syms[0]["location"]["uri"] == mod.as_uri(), syms)
            # Exercise the shipped one-shot client too, not only this test client.
            run = subprocess.run([sys.executable,
                                  os.path.join(ROOT, "scripts", "lsp_client.py"),
                                  "--def", str(main), "2", "16"],
                                 capture_output=True, text=True, timeout=15)
            result = json.loads(run.stdout) if run.returncode == 0 else None
            check("encoded folder CLI definition " + folder,
                  result and result["uri"] == mod.as_uri(), run.stdout + run.stderr)
        finally:
            c.close()

sys.path.insert(0, ROOT)
import lsp
for uri, expected in (
        ("file:///tmp/a%20b%23c%25d.holy", "/tmp/a b#c%d.holy"),
        ("file://localhost/tmp/a%2520.holy", "/tmp/a%20.holy"),
        ("file://other-host/tmp/a.holy", None),
        ("https://example.com/a.holy", None),
        ("untitled:buffer", None),
        ("file:relative.holy", None),
        ("file:///tmp/a.holy?query", None),
        ("file:///tmp/a.holy#fragment", None),
        ("file:///tmp/%00.holy", None),
        ("file:///tmp/%FF.holy", None),
        ("file://[invalid/tmp/a.holy", None)):
    check("file URI decode " + uri, lsp.uri_to_path(uri) == expected)

# Initialized single-root workspace discovery is independent of didOpen.
def workspace_case(name, initialize, opened=None, query="marker"):
    c = Client()
    try:
        capabilities = c.request("initialize", dict(
            {"capabilities": {}}, **initialize))["capabilities"]
        c.notify("initialized", {})
        if opened:
            path, text = opened
            c.notify("textDocument/didOpen", {"textDocument": {
                "uri": path.as_uri(), "languageId": "holyshit",
                "text": text, "version": 1}})
        try:
            result = c.request("workspace/symbol", {"query": query})
        except RuntimeError as error:
            check(name + " response", False, str(error))
            return None
        check(name + " no multi-root advertisement",
              "workspaceFolders" not in capabilities.get("workspace", {}))
        return result
    finally:
        c.close()


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / "project spaces#%20?ไทย😀"
    (root / "src").mkdir(parents=True)
    (root / "sibling").mkdir()
    main = root / "src/main.holy"
    main.write_text("def marker_disk():\n  return 1\n", encoding="utf-8")
    sibling = root / "sibling/lib.hs"
    sibling.write_text("def marker_sibling():\n  return 2\n", encoding="utf-8")
    for excluded in (".git", "legacy", "__pycache__"):
        (root / excluded).mkdir()
        (root / excluded / "hidden.holy").write_text(
            "def marker_hidden():\n  return 0\n")
    outside = Path(tmp) / "outside"
    outside.mkdir()
    (outside / "elsewhere.holy").write_text(
        "def marker_outside():\n  return 0\n")
    (root / "linked").symlink_to(outside, target_is_directory=True)
    expected = {"marker_disk", "marker_sibling"}
    for label, params in (
            ("root URI", {"rootUri": root.as_uri()}),
            ("root path", {"rootPath": str(root)}),
            ("localhost root", {"rootUri": root.as_uri().replace(
                "file:///", "file://localhost/", 1)}),
            ("root URI precedence", {"rootUri": root.as_uri(),
                                     "rootPath": str(outside)})):
        for opened in (None, (main, main.read_text())):
            name = label + (" before open" if opened is None else " nested open")
            result = workspace_case(name, params, opened)
            check(name + " sibling discovery and exclusions",
                  result is not None and {x["name"] for x in result} == expected,
                  result)
            check(name + " escaped sibling location", result is not None
                  and any(x["location"]["uri"] == sibling.as_uri()
                          for x in result), result)
    result = workspace_case("unsaved buffer", {"rootUri": root.as_uri()},
                            (main, "def marker_unsaved():\n  return 3\n"))
    check("unsaved buffer shadows disk once", result is not None
          and sorted(x["name"] for x in result)
          == ["marker_sibling", "marker_unsaved"], result)
    result = workspace_case("no root no open", {})
    check("no root no open empty", result == [], result)
    result = workspace_case("no root fallback", {}, (main, main.read_text()))
    check("no root uses document directory", result is not None
          and [x["name"] for x in result] == ["marker_disk"], result)
    result = workspace_case("unsupported folders", {"workspaceFolders": [
        {"uri": root.as_uri(), "name": "project"}]})
    check("unsupported folders do not scan", result == [], result)
    for label, params in (
            ("remote URI", {"rootUri": "file://remote" + str(root),
                             "rootPath": str(root)}),
            ("nonfile URI", {"rootUri": "https://example.com/project"}),
            ("relative path", {"rootPath": "relative"}),
            ("invalid root type", {"rootUri": 42}),
            ("NUL path", {"rootPath": str(root) + "\0"})):
        result = workspace_case(label, params)
        check(label + " does not scan", result == [], result)
    # Preserve HSPATH discovery without changing import lookup semantics.
    previous = os.environ.get("HSPATH")
    os.environ["HSPATH"] = str(outside)
    try:
        result = workspace_case("HSPATH without document", {})
        check("HSPATH without document discovered", result is not None
              and [x["name"] for x in result] == ["marker_outside"], result)
    finally:
        if previous is None:
            os.environ.pop("HSPATH", None)
        else:
            os.environ["HSPATH"] = previous

# References discover unopened sibling consumers without changing imports.
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "src").mkdir()
    (root / "sibling").mkdir()
    main = root / "src/main.holy"
    (root / "src/lib.holy").write_text("def shared(x):\n  return x * 2\n")
    source = "import lib\nprint lib.shared(1)\n"
    main.write_text(source)
    consumer = root / "sibling/use.holy"
    consumer.write_text("import lib\nprint lib.shared(2)\n")
    previous = os.environ.get("HSPATH")
    os.environ["HSPATH"] = str(root / "src")
    c = Client()
    try:
        c.request("initialize", {"rootUri": root.as_uri(), "capabilities": {}})
        c.notify("initialized", {})
        c.notify("textDocument/didOpen", {"textDocument": {
            "uri": main.as_uri(), "languageId": "holyshit", "text": source,
            "version": 1}})
        result = c.request("textDocument/references", {
            "textDocument": {"uri": main.as_uri()},
            "position": {"line": 1, "character": 12},
            "context": {"includeDeclaration": False}})
        check("references include unopened sibling consumer",
              {r["uri"] for r in result} == {main.as_uri(), consumer.as_uri()},
              result)
    finally:
        c.close()
        if previous is None:
            os.environ.pop("HSPATH", None)
        else:
            os.environ["HSPATH"] = previous

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for i in range(410):
        (root / ("file%03d.holy" % i)).write_text(
            "def marker_%03d():\n  return %d\n" % (i, i))
    result = workspace_case("bounded discovery", {"rootUri": root.as_uri()})
    check("existing discovery limit is 401", result is not None
          and len(result) == 401, len(result) if result is not None else None)
    many = root / "many.holy"
    text = "".join("def marker_%03d():\n  return %d\n" % (i, i)
                   for i in range(510))
    result = workspace_case("bounded symbols", {}, (many, text))
    check("existing symbol limit is 500", result is not None
          and len(result) == 500, len(result) if result is not None else None)

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
