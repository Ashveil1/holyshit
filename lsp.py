#!/usr/bin/env python3
"""holyshit language server (LSP over stdio, zero dependencies).

    python3 lsp.py                  # speak LSP on stdin/stdout
    python3 hs.py lsp               # same thing

Features: diagnostics (parse + scope check), hover (builtins, keywords,
user symbols), completion, goto-definition (same file + into modules),
document symbols, whole-document formatting via fmt.py.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import interp
from interp import HSErr

try:
    import fmt as _fmt
except ImportError:
    _fmt = None

try:
    from scripts import lang_data
except ImportError:
    import scripts.lang_data as lang_data


# ---------- UTF-16 position helpers (LSP uses UTF-16 code units) ----------

def _utf16_units(s):
    return len(s.encode("utf-16-le")) // 2


def col_to_idx(line_text, col):
    """LSP character (UTF-16) -> Python str index."""
    if col <= 0:
        return 0
    units = 0
    for i, ch in enumerate(line_text):
        units += 1 if ord(ch) < 0x10000 else 2
        if units > col:
            return i
    return len(line_text)


def col_from_idx(line_text, idx):
    idx = max(0, min(idx, len(line_text)))
    return _utf16_units(line_text[:idx])


def word_at(line_text, idx):
    """Return (word, start_idx, end_idx) around str index, [A-Za-z0-9_.]."""
    m = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*").finditer(line_text)
    for mm in m:
        if mm.start() <= idx <= mm.end() and mm.end() > mm.start():
            return mm.group(0), mm.start(), mm.end()
    # cursor between words / on digits: fall back to alnum run
    m2 = re.compile(r"[A-Za-z0-9_.]+").finditer(line_text)
    for mm in m2:
        if mm.start() <= idx <= mm.end():
            return mm.group(0), mm.start(), mm.end()
    return "", idx, idx


# ---------- document model ----------

class Doc:
    def __init__(self, uri, text, version=0):
        self.uri = uri
        self.text = text
        self.version = version
        self.path = uri_to_path(uri)
        self.ast = None
        self.perr = None
        self.serr = None
        self.symbols = []   # flat: dicts name/kind/line/detail/scope
        self.uses = []      # dicts name/line/occ/scopes
        self.analyze()

    def lines(self):
        return self.text.split("\n")

    def analyze(self):
        self.ast = None
        self.perr = None
        self.serr = None
        self.symbols = []
        self.uses = []
        interp.reset_parse_state()
        try:
            self.ast = interp.parse_program(self.text)
        except HSErr as e:
            self.perr = e
            return
        _collect(self.ast, self)
        # scope/symbol check, same as `hs.py check`
        try:
            import hs as _hs
            interp.reset_parse_state()
            _hs.Gen(self.ast, self.path or "<main>").scan()
        except HSErr as e:
            self.serr = e
        except Exception:
            pass


def uri_to_path(uri):
    if uri.startswith("file://"):
        return uri[len("file://"):]
    return None


def _walk(node, visit):
    # visit(node, parent_chain) for every AST dict with a "t" key
    stack = [(node, ())]
    while stack:
        cur, chain = stack.pop()
        if isinstance(cur, dict):
            if "t" in cur:
                visit(cur, chain)
                chain = chain + (cur,)
            for v in cur.values():
                if isinstance(v, (dict, list)):
                    stack.append((v, chain))
        elif isinstance(cur, list):
            for v in cur:
                if isinstance(v, (dict, list)):
                    stack.append((v, chain))


class _Scope:
    def __init__(self, parent=None, is_func=False):
        self.parent = parent
        self.is_func = is_func
        self.names = {}  # name -> symbol dict


def _collect(body, doc):
    root = _Scope()

    def bind(sc, name, kind, line, detail=""):
        sym = {"name": name, "kind": kind, "line": line, "detail": detail}
        sc.names.setdefault(name, sym)
        doc.symbols.append(sym)
        return sym

    occ = {}  # (line, name) -> count so far

    def use(sc, name, line):
        key = (line, name)
        idx = occ.get(key, 0)
        occ[key] = idx + 1
        doc.uses.append({"name": name, "line": line, "occ": idx,
                         "scopes": _chain(sc)})

    def _chain(sc):
        out = []
        while sc is not None:
            out.append(sc)
            sc = sc.parent
        return out

    def stmts(body, sc):
        for s in body:
            st = s.get("t")
            if st == "def":
                params = s.get("params", [])
                bind(sc, s["name"], "function", s["line"],
                     "(%s)" % ", ".join(params))
                fs = _Scope(sc, True)
                for p in params:
                    bind(fs, p, "param", s["line"])
                stmts(s.get("body", []), fs)
            elif st == "set":
                bind(sc, s["name"], "variable", s["line"])
                expr(s.get("val"), sc)
            elif st == "for":
                bind(sc, s.get("var"), "variable", s["line"])
                expr(s.get("iter"), sc)
                stmts(s.get("body", []), sc)
            elif st == "import":
                bind(sc, s["name"].split(".")[0], "module", s["line"],
                     s["name"])
            elif st == "try":
                stmts(s.get("body", []), sc)
                if s.get("ebody") is not None:
                    if s.get("ename"):
                        bind(sc, s["ename"], "variable", s["line"],
                             "exception string")
                    stmts(s["ebody"], sc)
                if s.get("fbody") is not None:
                    stmts(s["fbody"], sc)
            elif st == "if":
                expr(s.get("cond"), sc)
                stmts(s.get("then", []), sc)
                for ec, eb in s.get("elifs", []):
                    expr(ec, sc)
                    stmts(eb, sc)
                stmts(s.get("els", []), sc)
            elif st == "while":
                expr(s.get("cond"), sc)
                stmts(s.get("body", []), sc)
            elif st == "return":
                if s.get("val") is not None:
                    expr(s["val"], sc)
            elif st == "raise":
                if s.get("val") is not None:
                    expr(s["val"], sc)
            elif st == "print":
                for a in s.get("args", []):
                    expr(a, sc)
            elif st == "expr":
                expr(s.get("val"), sc)
            elif st == "setindex":
                expr(s.get("obj"), sc)
                expr(s.get("idx"), sc)
                expr(s.get("val"), sc)
            elif st == "setattr":
                expr(s.get("obj"), sc)
                expr(s.get("val"), sc)
            elif st == "unsafe":
                for x in s.get("body", []):
                    ustmt(x, sc)
            elif st in ("global", "extern", "struct", "pass", "break",
                        "continue"):
                pass

    def ustmt(x, sc):
        t = x.get("t")
        if t in ("udecl", "store", "fstore", "struct", "expr", "print",
                 "if", "while", "return", "break", "continue", "set",
                 "global", "raise"):
            stmts([x], sc)

    def expr(e, sc):
        if not isinstance(e, dict) or "t" not in e:
            return
        t = e["t"]
        if t == "var":
            use(sc, e["name"], e.get("line", 0))
        elif t in ("neg", "not", "deref"):
            expr(e.get("val"), sc)
        elif t == "bin":
            expr(e.get("l"), sc)
            expr(e.get("r"), sc)
        elif t == "call":
            expr(e.get("fn"), sc)
            for a in e.get("args", []):
                expr(a, sc)
        elif t == "index":
            expr(e.get("obj"), sc)
            expr(e.get("idx"), sc)
        elif t == "slice":
            expr(e.get("obj"), sc)
            if e.get("start") is not None:
                expr(e["start"], sc)
            if e.get("stop") is not None:
                expr(e["stop"], sc)
        elif t == "attr":
            expr(e.get("obj"), sc)
        elif t == "list":
            for a in e.get("items", []):
                expr(a, sc)
        elif t == "dict":
            for k, v in e.get("pairs", []):
                expr(k, sc)
                expr(v, sc)
        elif t in ("field",):
            expr(e.get("obj"), sc)
            if e.get("idx") is not None:
                expr(e.get("idx"), sc)

    stmts(body, root)


def find_use(doc, line1, name, occ_idx):
    for u in doc.uses:
        if u["line"] == line1 and u["name"] == name and u["occ"] == occ_idx:
            return u
    for u in doc.uses:
        if u["line"] == line1 and u["name"] == name:
            return u
    return None


def resolve_use(use):
    """Nearest visible binding for a recorded use -> symbol or None."""
    for sc in use["scopes"]:
        if use["name"] in sc.names:
            return sc.names[use["name"]]
    return None


# ---------- module resolution (for cross-file definition) ----------

def find_module_file(dotted, basedir):
    rel = dotted.replace(".", "/") + ".hs"
    dirs = []
    if basedir:
        dirs.append(basedir)
    dirs.extend(d for d in os.environ.get("HSPATH", "").split(":") if d)
    dirs.append(os.getcwd())
    for d in dirs:
        if not d:
            continue
        p = os.path.abspath(os.path.join(d, rel))
        if os.path.isfile(p):
            return p
    return None


_mod_cache = {}  # path -> Doc-ish (ast, symbols, error)


def load_module_doc(path):
    if path in _mod_cache:
        return _mod_cache[path]
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    interp.reset_parse_state()
    try:
        ast = interp.parse_program(text)
    except HSErr:
        return None
    doc = {"path": path, "text": text, "ast": ast, "symbols": [], "uses": []}
    fake = type("D", (), {})()
    fake.symbols = doc["symbols"]
    fake.uses = doc["uses"]
    _collect(ast, fake)
    _mod_cache[path] = doc
    return doc


def top_symbol(symbols, name):
    for s in symbols:
        if s["name"] == name:
            return s
    return None


# ---------- LSP server ----------

class Server:
    def __init__(self, rin, wout):
        self.rin = rin
        self.wout = wout
        self.docs = {}
        self.shutdown = False
        self.root = None

    def run(self):
        while True:
            msg = self.read_msg()
            if msg is None:
                break
            self.handle(msg)
            if msg.get("method") == "exit":
                break

    def read_msg(self):
        headers = {}
        while True:
            line = self.rin.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                break
            if b":" in line:
                k, v = line.split(b":", 1)
                headers[k.strip().lower()] = v.strip()
        length = int(headers.get(b"content-length", 0))
        if not length:
            return None
        body = b""
        while len(body) < length:
            chunk = self.rin.read(length - len(body))
            if not chunk:
                break
            body += chunk
        try:
            return json.loads(body.decode("utf-8"))
        except ValueError:
            return None

    def send(self, obj):
        body = json.dumps(obj).encode("utf-8")
        self.wout.write(b"Content-Length: %d\r\n\r\n" % len(body))
        self.wout.write(body)
        self.wout.flush()

    def reply(self, mid, result):
        self.send({"jsonrpc": "2.0", "id": mid, "result": result})

    def error(self, mid, code, message):
        if mid is None:
            return
        self.send({"jsonrpc": "2.0", "id": mid,
                   "error": {"code": code, "message": message}})

    def notify(self, method, params):
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def handle(self, msg):
        method = msg.get("method", "")
        mid = msg.get("id")
        params = msg.get("params", {}) or {}
        try:
            if method == "initialize":
                self.root = (params.get("rootUri")
                             or params.get("rootPath"))
                self.reply(mid, {
                    "capabilities": {
                        "textDocumentSync": 1,
                        "hoverProvider": True,
                        "completionProvider": {"triggerCharacters": ["."]},
                        "definitionProvider": True,
                        "documentSymbolProvider": True,
                        "documentFormattingProvider": True,
                    },
                    "serverInfo": {"name": "holyshit-lsp", "version": "0.5.0"},
                })
            elif method == "initialized":
                pass
            elif method == "shutdown":
                self.shutdown = True
                self.reply(mid, None)
            elif method == "exit":
                pass
            elif method == "textDocument/didOpen":
                td = params["textDocument"]
                self.docs[td["uri"]] = Doc(td["uri"], td["text"],
                                           td.get("version", 0))
                self.push_diagnostics(td["uri"])
            elif method == "textDocument/didChange":
                uri = params["textDocument"]["uri"]
                ver = params["textDocument"].get("version", 0)
                for ch in params.get("contentChanges", []):
                    # full sync only
                    self.docs[uri] = Doc(uri, ch.get("text", ""), ver)
                self.push_diagnostics(uri)
            elif method == "textDocument/didClose":
                uri = params["textDocument"]["uri"]
                self.docs.pop(uri, None)
            elif method == "textDocument/hover":
                self.reply(mid, self.hover(params))
            elif method == "textDocument/completion":
                self.reply(mid, self.complete(params))
            elif method == "textDocument/definition":
                self.reply(mid, self.definition(params))
            elif method == "textDocument/documentSymbol":
                self.reply(mid, self.symbols(params))
            elif method == "textDocument/formatting":
                self.reply(mid, self.formatting(params))
            else:
                if mid is not None:
                    self.error(mid, -32601, f"unknown method {method}")
        except Exception as e:  # never kill the server on a bad request
            self.error(mid, -32603, f"{type(e).__name__}: {e}")

    # ----- features -----

    def get_doc(self, params):
        return self.docs.get(params["textDocument"]["uri"])

    def pos_word(self, params):
        doc = self.get_doc(params)
        if doc is None:
            return None, None, None, None
        pos = params["position"]
        ln = pos["line"]
        lines = doc.lines()
        if ln < 0 or ln >= len(lines):
            return doc, None, None, None
        text = lines[ln]
        idx = col_to_idx(text, pos.get("character", 0))
        word, s, e = word_at(text, idx)
        return doc, word, (ln, s, e), idx

    def push_diagnostics(self, uri):
        doc = self.docs.get(uri)
        if doc is None:
            return
        diags = []
        nlines = max(1, len(doc.lines()))
        for err in (doc.perr, doc.serr):
            if err is None:
                continue
            ln = max(1, err.line or 1)
            ln = min(ln, nlines)
            line_text = doc.lines()[ln - 1] if ln - 1 < len(doc.lines()) else ""
            diags.append({
                "range": {
                    "start": {"line": ln - 1, "character": 0},
                    "end": {"line": ln - 1,
                            "character": col_from_idx(line_text,
                                                      len(line_text))},
                },
                "severity": 1,
                "source": "hs",
                "message": err.msg,
            })
        self.notify("textDocument/publishDiagnostics",
                    {"uri": uri, "diagnostics": diags})

    def hover(self, params):
        doc, word, span, idx = self.pos_word(params)
        if doc is None or not word:
            return None
        base = word.split(".")[0]
        if word in lang_data.BUILTINS:
            sig, desc, be = lang_data.BUILTINS[word]
            return {"contents": {"kind": "markdown",
                                 "value": f"**`{sig}`**\n\n{desc}\n\n_backends:_ "
                                 + ", ".join(sorted(be))}}
        if word in lang_data.KEYWORDS:
            return {"contents": {"kind": "markdown",
                                 "value": f"**`{word}`** (keyword)\n\n"
                                 + lang_data.KEYWORDS[word]}}
        # user symbol: resolve through scope chain
        line1 = span[0] + 1
        occ = self.occ_index(doc, span, idx, base if "." in word else word)
        use = find_use(doc, line1, base if "." in word else word, occ)
        if use is not None:
            sym = resolve_use(use)
            if sym is not None:
                return {"contents": {"kind": "markdown",
                                     "value": self.sym_hover(sym)}}
        # dotted module attribute: describe the module part
        if "." in word:
            use = find_use(doc, line1, base, occ)
            if use is not None:
                sym = resolve_use(use)
                if sym is not None and sym["kind"] == "module":
                    return {"contents": {"kind": "markdown",
                                         "value": self.sym_hover(sym)}}
        return None

    def occ_index(self, doc, span, idx, name):
        # which occurrence of `name` on this line is the cursor on?
        ln, s, e = span
        text = doc.lines()[ln]
        count = 0
        for mm in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", text):
            if mm.group(0) == name:
                if mm.start() <= idx <= mm.end():
                    return count
                count += 1
        return 0

    def sym_hover(self, sym):
        kind = sym["kind"]
        if kind == "function":
            return (f"**`def {sym['name']}{sym.get('detail', '')}`**\n\n"
                    f"function defined at line {sym['line']}")
        if kind == "param":
            return (f"**`{sym['name']}`** (parameter)\n\n"
                    f"declared at line {sym['line']}")
        if kind == "module":
            return (f"**`import {sym.get('detail', sym['name'])}`**\n\n"
                    f"module imported at line {sym['line']}")
        return (f"**`{sym['name']}`** ({kind})\n\n"
                f"defined at line {sym['line']}")

    def complete(self, params):
        doc, word, span, idx = self.pos_word(params)
        items = []
        for kw, desc in sorted(lang_data.KEYWORDS.items()):
            items.append({"label": kw, "kind": 14, "detail": "keyword",
                          "documentation": desc})
        for name, (sig, desc, be) in sorted(lang_data.BUILTINS.items()):
            items.append({"label": name, "kind": 3, "detail": sig,
                          "documentation": f"{desc} [{', '.join(sorted(be))}]"})
        if doc is not None:
            seen = set()
            for s in doc.symbols:
                if s["name"] in seen:
                    continue
                seen.add(s["name"])
                kind = {"function": 3, "module": 9}.get(s["kind"], 6)
                items.append({"label": s["name"], "kind": kind,
                              "detail": f"{s['kind']} (line {s['line']})"})
        return {"isIncomplete": False, "items": items}

    def definition(self, params):
        doc, word, span, idx = self.pos_word(params)
        if doc is None or not word:
            return None
        line1 = span[0] + 1
        parts = word.split(".")
        base = parts[0]
        occ = self.occ_index(doc, span, idx, base)
        use = find_use(doc, line1, base, occ)
        if use is None:
            # maybe the cursor is on the import binding itself
            for s in doc.symbols:
                if s["kind"] == "module" and s["name"] == base \
                        and s["line"] <= line1:
                    path = self.module_path(doc, s.get("detail") or base)
                    if path:
                        return self.loc(path, 0)
                    return None
            return None
        sym = resolve_use(use)
        if sym is None:
            return None
        if len(parts) == 1:
            if sym["kind"] == "module":
                path = self.module_path(doc, sym.get("detail") or sym["name"])
                if path:
                    return self.loc(path, 0)
                return None
            return self.loc(doc.path, sym["line"] - 1, sym["name"])
        # mod.attr[.attr...]: walk into module files
        names = parts[1:]
        cur_path = self.module_path(doc, sym.get("detail") or sym["name"])
        for i, attr in enumerate(names):
            if cur_path is None:
                return None
            mdoc = load_module_doc(cur_path)
            if mdoc is None:
                return None
            target = top_symbol(mdoc["symbols"], attr)
            last = (i == len(names) - 1)
            if target is None:
                return None
            if not last:
                # intermediate must be a submodule: mod.attr where attr is module
                sub = self.submodule_path(cur_path, attr)
                if sub is None:
                    # re-exported import inside the module file
                    sub = self.reexport_path(mdoc, attr)
                    if sub is None:
                        return None
                cur_path = sub
                continue
            if target["kind"] == "module":
                sub = (self.submodule_path(cur_path, attr)
                       or self.reexport_path(mdoc, attr))
                if sub is None:
                    return None
                return self.loc(sub, 0)
            return self.loc(cur_path, target["line"] - 1, target["name"])
        return None

    def module_path(self, doc, dotted):
        basedir = None
        if doc.path:
            basedir = os.path.dirname(os.path.abspath(doc.path))
        return find_module_file(dotted, basedir)

    def submodule_path(self, mod_path, attr):
        base = os.path.dirname(mod_path)
        stem = os.path.splitext(os.path.basename(mod_path))[0]
        cand = os.path.join(base, stem, attr + ".hs")
        if os.path.isfile(cand):
            return cand
        # sibling file like pkg/mod.hs when mod_path is pkg.hs
        cand2 = os.path.join(base, stem + "_" + attr + ".hs")
        if os.path.isfile(cand2):
            return cand2
        return None

    def reexport_path(self, mdoc, attr):
        # `import x` inside the module file re-exports x as mod.x
        for s in mdoc["symbols"]:
            if s["kind"] == "module" and s["name"] == attr:
                return self.module_path(
                    type("D", (), {"path": mdoc["path"]})(), s.get("detail")
                    or attr)
        return None

    def loc(self, path, line0, name=""):
        uri = "file://" + path if path else None
        if path and os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read().split("\n")[line0]
            except (OSError, IndexError):
                text = ""
        else:
            text = ""
        m = re.search(r"\b%s\b" % re.escape(name), text) if name else None
        c0 = col_from_idx(text, m.start()) if m else 0
        c1 = col_from_idx(text, m.end()) if m else len(text)
        return {"uri": uri,
                "range": {"start": {"line": max(0, line0), "character": c0},
                          "end": {"line": max(0, line0), "character": c1}}}

    def symbols(self, params):
        doc = self.get_doc(params)
        if doc is None or doc.ast is None:
            return []
        out = []
        for s in doc.symbols:
            kind = {"function": 12, "module": 2, "param": 13}.get(s["kind"], 13)
            ln = max(0, s["line"] - 1)
            out.append({"name": s["name"], "kind": kind,
                        "range": {"start": {"line": ln, "character": 0},
                                  "end": {"line": ln, "character": 0}},
                        "selectionRange": {
                            "start": {"line": ln, "character": 0},
                            "end": {"line": ln, "character": 0}}})
        return out

    def formatting(self, params):
        doc = self.get_doc(params)
        if doc is None or doc.ast is None or _fmt is None:
            return []
        try:
            interp.reset_parse_state()
            ast = interp.parse_program(doc.text)
            out = _fmt.fmt_program(ast)
        except HSErr:
            return []
        if out == doc.text:
            return []
        nlines = len(doc.lines())
        last = doc.lines()[-1] if doc.lines() else ""
        return [{"range": {"start": {"line": 0, "character": 0},
                           "end": {"line": nlines - 1,
                                   "character": col_from_idx(last, len(last))}},
                 "newText": out}]


def main():
    srv = Server(sys.stdin.buffer, sys.stdout.buffer)
    srv.run()


if __name__ == "__main__":
    main()
