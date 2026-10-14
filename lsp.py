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
            self.ast = interp.parse_program(self.text, raw=True)
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

    @classmethod
    def from_module_doc(cls, path, mdoc):
        """Wrap an already-parsed module (load_module_doc) without re-parsing."""
        d = cls.__new__(cls)
        d.uri = "file://" + path
        d.text = mdoc["text"]
        d.version = 0
        d.path = path
        d.ast = mdoc["ast"]
        d.perr = None
        d.serr = None
        d.symbols = mdoc["symbols"]
        d.uses = mdoc["uses"]
        return d


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
                sym = bind(sc, s["name"], "function", s["line"],
                           "(%s)" % ", ".join(params))
                sym["params"] = list(params)
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
        ast = interp.parse_program(text, raw=True)
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
                        "referencesProvider": True,
                        "documentHighlightProvider": True,
                        "signatureHelpProvider": {"triggerCharacters":
                                                  ["(", ",", ")"]},
                        "documentSymbolProvider": True,
                        "workspaceSymbolProvider": True,
                        "documentFormattingProvider": True,
                    },
                    "serverInfo": {"name": "holyshit-lsp", "version": "0.6.0"},
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
            elif method == "textDocument/references":
                ctx = params.get("context") or {}
                self.reply(mid, self.references(params,
                                               ctx.get("includeDeclaration",
                                                       True)))
            elif method == "textDocument/documentHighlight":
                self.reply(mid, self.document_highlight(params))
            elif method == "textDocument/signatureHelp":
                self.reply(mid, self.signature_help(params))
            elif method == "workspace/symbol":
                self.reply(mid, self.workspace_symbol(params))
            elif method == "textDocument/didSave":
                uri = params["textDocument"]["uri"]
                # editors that send includeText give us the freshest buffer
                if "text" in params:
                    self.docs[uri] = Doc(uri, params["text"],
                                        params["textDocument"].get("version", 0))
                self.push_diagnostics(uri)
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
        if "." not in word:
            if word in lang_data.BUILTINS:
                sig, desc, be = lang_data.BUILTINS[word]
                return {"contents": {"kind": "markdown",
                                     "value": f"**`{sig}`**\n\n{desc}\n\n"
                                              f"_backends:_ "
                                              + ", ".join(sorted(be))}}
            if word in lang_data.KEYWORDS:
                return {"contents": {"kind": "markdown",
                                     "value": f"**`{word}`** (keyword)\n\n"
                                              + lang_data.KEYWORDS[word]}}
        sym, path = self.resolve_parts(doc, word.split("."), span[0] + 1,
                                       self.occ_index(doc, span, idx, base))
        if sym is not None:
            txt = self.sym_hover(sym)
            if path and doc.path and \
                    os.path.abspath(path) != os.path.abspath(doc.path):
                txt += f"\n\n_defined in_ `{os.path.basename(path)}`"
            return {"contents": {"kind": "markdown", "value": txt}}
        return None

    def resolve_parts(self, doc, parts, line1, occ):
        """Resolve a (possibly dotted) name -> (symbol, defining file).

        Returns (None, None) when nothing is found. The returned path is the
        file the symbol lives in; for `mod.attr` that is the module file, for a
        local variable it is the current document.
        """
        base = parts[0]
        use = find_use(doc, line1, base, occ)
        sym = resolve_use(use) if use is not None else None
        if sym is None:
            # cursor sits on the definition itself (no `use` recorded there)
            kinds = ("function", "module", "variable")
            cands = [s for s in doc.symbols
                     if s["name"] == base and s["line"] == line1
                     and s["kind"] in kinds]
            if not cands:
                cands = [s for s in doc.symbols
                         if s["kind"] == "module" and s["name"] == base
                         and s["line"] <= line1]
            sym = cands[-1] if cands else None
        if sym is None:
            return None, None
        if len(parts) == 1:
            if sym["kind"] == "module":
                return sym, self.module_path(doc, sym.get("detail") or
                                             sym["name"])
            return sym, doc.path
        if sym["kind"] != "module":
            return None, None
        cur = self.module_path(doc, sym.get("detail") or sym["name"])
        for i, attr in enumerate(parts[1:]):
            if cur is None:
                return None, None
            mdoc = load_module_doc(cur)
            if mdoc is None:
                return None, None
            tgt = top_symbol(mdoc["symbols"], attr)
            if tgt is None:
                return None, None
            last = (i == len(parts) - 2)
            if tgt["kind"] == "module":
                sub = (self.submodule_path(cur, attr)
                       or self.reexport_path(mdoc, attr))
                if last:
                    return tgt, sub
                if sub is None:
                    return None, None
                cur = sub
                continue
            if last:
                return tgt, cur
            return None, None
        return None, None

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
        # `mod.` / `mod.pre` -> complete the module's top-level names only
        if doc is not None and "." in word:
            members = self.member_items(doc, word, span, idx)
            if members is not None:
                return {"isIncomplete": False, "items": members}
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

    def member_items(self, doc, word, span, idx):
        """Completion items for `mod.attr...`. None = not a module path."""
        parts = word.split(".")
        parent = parts[:-1]
        if not parent or not all(parent):
            return None
        sym, path = self.resolve_parts(doc, parent, span[0] + 1,
                                       self.occ_index(doc, span, idx,
                                                      parent[0]))
        if path is None or sym is None:
            return None
        mdoc = load_module_doc(path)
        if mdoc is None:
            return None
        items = []
        seen = set()
        for s in mdoc["symbols"]:
            # top-level names only: params/locals are not `mod.attr`
            if s["kind"] == "param" or s["name"] in seen:
                continue
            seen.add(s["name"])
            items.append({
                "label": s["name"],
                "kind": {"function": 3, "module": 9, "param": 6}.get(s["kind"],
                                                                    6),
                "detail": (f"{s['kind']} ({os.path.basename(path)}:"
                           f"{s['line']})"),
                "documentation": {"kind": "markdown",
                                  "value": self.sym_hover(s)},
            })
        return items

    # ----- references / highlights / signature help / workspace symbols -----

    def _index_docs(self, doc):
        """Open documents plus every .hs file next to this one (bounded)."""
        out = list(self.docs.values())
        if not doc.path:
            return out
        root = os.path.dirname(os.path.abspath(doc.path))
        for base in [root] + [d for d in
                              os.environ.get("HSPATH", "").split(":") if d]:
            if not os.path.isdir(base):
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames
                               if not d.startswith(".") and d != "legacy"
                               and d != "__pycache__"]
                for fn in sorted(filenames):
                    if not fn.endswith(".hs"):
                        continue
                    full = os.path.join(dirpath, fn)
                    if any(d.path == full for d in out):
                        continue
                    mdoc = load_module_doc(full)
                    if mdoc is not None:
                        out.append(Doc.from_module_doc(full, mdoc))
                    if len(out) > 400:
                        return out
        return out

    def references(self, params, include_declaration=True):
        doc, word, span, idx = self.pos_word(params)
        if doc is None or not word:
            return []
        parts = word.split(".")
        sym, path = self.resolve_parts(doc, parts, span[0] + 1,
                                       self.occ_index(doc, span, idx,
                                                      parts[0]))
        if sym is None or path is None:
            return []
        target = (os.path.abspath(path), sym["name"])
        out = []
        for d in self._index_docs(doc):
            if d.ast is None:
                continue
            for u in d.uses:
                if u["name"] != parts[0]:
                    continue
                s, p = self.resolve_parts(d, parts, u["line"], u["occ"])
                if s is None or p is None:
                    continue
                if (os.path.abspath(p), s["name"]) != target:
                    continue
                rng = self.word_range(d, u["line"] - 1, u["occ"], u["name"])
                if rng:
                    out.append({"uri": "file://" + d.path, "range": rng})
        if include_declaration:
            rng = self.word_range_file(path, sym["line"] - 1, sym["name"])
            if rng:
                decl = {"uri": "file://" + path, "range": rng}
                if decl not in out:
                    out.append(decl)
        # de-dup
        seen = set()
        uniq = []
        for r in out:
            k = (r["uri"], r["range"]["start"]["line"],
                 r["range"]["start"]["character"])
            if k not in seen:
                seen.add(k)
                uniq.append(r)
        return uniq

    def word_range(self, doc, line0, occ, name):
        """Range of the occ-th `name` on line0 of an open document."""
        if line0 >= len(doc.lines()):
            return None
        return self._range_in(doc.lines()[line0], occ, name, line0)

    def word_range_file(self, path, line0, name):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read().split("\n")
        except OSError:
            return None
        if line0 >= len(text):
            return None
        return self._range_in(text[line0], 0, name, line0)

    def _range_in(self, text, occ, name, line0):
        seen = 0
        for mm in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", text):
            if mm.group(0) != name:
                continue
            if seen == occ:
                return {"start": {"line": line0,
                                  "character": col_from_idx(text, mm.start())},
                        "end": {"line": line0,
                                "character": col_from_idx(text, mm.end())}}
            seen += 1
        return None

    def document_highlight(self, params):
        doc, word, span, idx = self.pos_word(params)
        if doc is None or not word:
            return []
        base = word.split(".")[0]
        sym, path = self.resolve_parts(doc, word.split("."), span[0] + 1,
                                       self.occ_index(doc, span, idx, base))
        out = []
        lines = [span[0]]
        if sym is not None and path and doc.path and \
                os.path.abspath(path) == os.path.abspath(doc.path or ""):
            lines.append(sym["line"] - 1)
        for ln in lines:
            if ln >= len(doc.lines()):
                continue
            text = doc.lines()[ln]
            for mm in re.finditer(r"\b%s\b" % re.escape(base), text):
                out.append({"range": {
                    "start": {"line": ln,
                              "character": col_from_idx(text, mm.start())},
                    "end": {"line": ln,
                            "character": col_from_idx(text, mm.end())}},
                    "kind": 1 if (ln == sym["line"] - 1) else 2})
        return out

    def signature_help(self, params):
        doc, word, span, idx = self.pos_word(params)
        if doc is None:
            return None
        text = doc.lines()[span[0]]
        prefix = text[:idx]
        op = prefix.rfind("(")
        if op < 0:
            return None
        depth = 0
        active = 0
        for ch in prefix[op:]:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 1:
                active += 1
        m = re.search(r"([A-Za-z_][A-Za-z0-9_.]*)\s*$", prefix[:op])
        if not m:
            return None
        callee = m.group(1)
        params_list, label, doc_txt = None, None, None
        if callee in lang_data.BUILTINS:
            sig, desc, _be = lang_data.BUILTINS[callee]
            label = sig.split("|")[0].strip()
            inner = label[len(callee):].strip()
            if inner.startswith("(") and inner.endswith(")"):
                params_list = [p.strip() for p in inner[1:-1].split(",")
                               if p.strip()]
            doc_txt = desc
        else:
            sym, _p = self.resolve_parts(doc, callee.split("."), span[0] + 1,
                                         self.occ_index(doc, span, idx,
                                                        callee.split(".")[0]))
            if sym is None or sym["kind"] != "function":
                return None
            params_list = sym.get("params") or []
            label = f"{sym['name']}({', '.join(params_list)})"
        sig = {"label": label,
               "parameters": [{"label": p} for p in params_list]}
        if doc_txt:
            sig["documentation"] = {"kind": "markdown", "value": doc_txt}
        if params_list:
            sig["activeParameter"] = min(active, len(params_list) - 1)
        return {"signatures": [sig], "activeSignature": 0,
                "activeParameter": sig.get("activeParameter", 0)}

    def workspace_symbol(self, params):
        query = (params.get("query") or "").lower()
        out = []
        first = list(self.docs.values())[0] if self.docs else None
        for d in self._index_docs(first):
            if d.ast is None:
                continue
            for s in d.symbols:
                if query and query not in s["name"].lower():
                    continue
                kind = {"function": 12, "module": 2, "param": 13}.get(s["kind"],
                                                                       13)
                ln = max(0, s["line"] - 1)
                rng = self.word_range(d, ln, 0, s["name"]) or {
                    "start": {"line": ln, "character": 0},
                    "end": {"line": ln, "character": 0}}
                out.append({"name": s["name"], "kind": kind,
                            "location": {"uri": "file://" + d.path,
                                         "range": rng},
                            "containerName": os.path.basename(d.path)})
        return out[:500]

    def definition(self, params):
        doc, word, span, idx = self.pos_word(params)
        if doc is None or not word:
            return None
        base = word.split(".")[0]
        sym, path = self.resolve_parts(doc, word.split("."), span[0] + 1,
                                       self.occ_index(doc, span, idx, base))
        if sym is None or not path:
            return None
        if sym["kind"] == "module":
            return self.loc(path, 0)
        return self.loc(path, sym["line"] - 1, sym["name"])

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
            ast = interp.parse_program(doc.text, raw=True)
            out = _fmt.fmt_program_c(ast, doc.text)
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
