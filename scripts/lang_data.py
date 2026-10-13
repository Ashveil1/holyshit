#!/usr/bin/env python3
"""Canonical language data for holyshit docs + LSP + agents.

Single source of truth for: keywords, builtin signatures/descriptions,
and per-backend support. interp.BUILTINS is still the runtime authority;
tests/test_docs.py asserts this table covers it exactly.

Support columns: interp, native (gcc), xbuild (x86-64 hosted subset),
xkernel (freestanding subset).
"""

KEYWORDS = {
    "def": "define a function: `def name(params):` + indented body",
    "if": "conditional branch (with `elif` / `else`)",
    "elif": "else-if branch after `if`",
    "else": "fallback branch for `if`",
    "while": "loop while a condition is truthy",
    "for": "loop `for x in LIST | range() | dict-keys`",
    "in": "membership in `for x in ...`",
    "return": "return a value from a function (bare `return` gives Null)",
    "break": "exit the innermost loop",
    "continue": "skip to the next loop iteration",
    "global": "write module-level names from inside a function",
    "import": "load a module: `import mod`, `import pkg.mod`",
    "try": "guarded block: needs `except` and/or `finally`",
    "except": "handler for a `try` block, optional `as e` (Str)",
    "as": "bind the error string in `except as e`",
    "finally": "cleanup block: runs on every exit of `try`",
    "raise": "`raise \"msg\"` throws; bare `raise` re-throws in `except`",
    "true": "boolean true",
    "false": "boolean false",
    "null": "the Null value",
    "and": "short-circuit and (returns an operand, not Bool)",
    "or": "short-circuit or (returns an operand, not Bool)",
    "not": "logical negation",
    "pass": "do nothing (empty block placeholder)",
    "unsafe": "low-level static block: I64/U64/Ptr + structs",
    "struct": "declare a struct layout inside `unsafe:`",
    "extern": "declare C-ABI functions from libc/.so/.c",
    "from": "used in `extern from \"lib\":`",
}

ALL = {"interp", "native", "xbuild", "xkernel"}
# everything that needs libc/stdin/argv works on the hosted x64 backend too
# (its File runtime is the same openat/read/write/getdents machinery)
HOSTED = {"interp", "native", "xbuild"}
NO_XBUILD = {"interp", "native", "xkernel"}  # kernel-surface via xkernel
# tcp_* / http_get: interp and native only (x64 has no sockets yet)
NET = {"interp", "native"}

# name -> (signature, description, support set)
BUILTINS = {
    "print": ("print x, y, ...", "print values space-separated + newline", ALL),
    "len": ("len(x)", "length of Str/List/Dict", ALL),
    "range": ("range(n) | range(a, b)", "Int list [0..n) or [a..b)", ALL),
    "str": ("str(x)", "convert any value to Str", ALL),
    "int": ("int(x)", "convert to Int", ALL),
    "float": ("float(x)", "convert to Float", ALL),
    "input": ("input()", "read one line from stdin (hosted only)", HOSTED),
    "open": ("open(path, mode)", "open a file (hosted only)", HOSTED),
    "read": ("read(f, n)", "read n bytes (hosted only)", HOSTED),
    "write": ("write(f, s)", "write Str (hosted only)", HOSTED),
    "close": ("close(f)", "close a file (hosted only)", HOSTED),
    "append": ("append(list, x)", "push x, returns Null", ALL),
    "split": ("split(s) | split(s, sep)", "split Str to List", ALL),
    "find": ("find(s, sub)", "byte index of sub or -1", ALL),
    "contains": ("contains(c, x)", "what `x in c` means: Str substring, List element or Dict key", ALL),
    "keys": ("keys(dict)", "List of the dict keys in insertion order", ALL),
    "values": ("values(dict)", "List of the dict values in insertion order", ALL),
    "has": ("has(dict, key)", "true when the dict has the key", ALL),
    "join": ("join(sep, list)", "join List of Str", ALL),
    "argv": ("argv()", "program args as List (hosted only)", HOSTED),
    "env": ("env(name)", "env var or Null (hosted only)", HOSTED),
    "system": ("system(cmd)", "run shell command, exit code (hosted only)",
               HOSTED),
    "tcp_connect": ("tcp_connect(host, port)", "open TCP (hosted only)",
                    NET),
    "tcp_send": ("tcp_send(sock, s)", "send bytes (hosted only)", NET),
    "tcp_recv": ("tcp_recv(sock, n)", "recv bytes (hosted only)", NET),
    "tcp_close": ("tcp_close(sock)", "close socket (hosted only)", NET),
    "tcp_listen": ("tcp_listen(port)", "listen socket (hosted only)", NET),
    "tcp_accept": ("tcp_accept(sock)", "accept client (hosted only)", NET),
    "http_get": ("http_get(url)", "http GET body as Str (hosted only)",
                 NET),
    "json_parse": ("json_parse(s)", "parse JSON Str", ALL),
    "json_str": ("json_str(x)", "value to JSON Str", ALL),
    "read_mem": ("read_mem(ptr, n)", "n raw bytes as Str (all backends)",
                 ALL),
    "read_text": ("read_text(path)", "whole file as Str (hosted only)",
                  HOSTED),
    "write_text": ("write_text(path, s)", "write file (hosted only)", HOSTED),
    "append_text": ("append_text(path, s)", "append file (hosted only)",
                    HOSTED),
    "exists": ("exists(path)", "path exists? (hosted only)", HOSTED),
    "ls": ("ls(path)", "dir entries List (hosted only)", HOSTED),
    "mkdir": ("mkdir(path)", "make directory (hosted only)", HOSTED),
    "json_load": ("json_load(path)", "load JSON file (hosted only)", HOSTED),
    "json_save": ("json_save(path, x)", "save value as JSON (hosted only)",
                  HOSTED),
    # unsafe builtins (raw machine words, inside unsafe: only)
    "alloc": ("alloc(n)", "zeroed n bytes (unsafe only)", ALL),
    "load8": ("load8(p)", "load byte (unsafe only)", ALL),
    "load32": ("load32(p)", "load 4 bytes (unsafe only)", ALL),
    "load64": ("load64(p)", "load 8 bytes raw (unsafe only; page tables)", ALL),
    "store8": ("store8(p, v)", "store byte (unsafe only)", ALL),
    "store32": ("store32(p, v)", "store 4 bytes (unsafe only)", ALL),
    "store64": ("store64(p, v)", "store 8 bytes raw (unsafe only; page tables)",
                ALL),
    "as_ptr": ("as_ptr(x)", "Int value -> Ptr (unsafe only)", ALL),
    "as_int": ("as_int(p)", "Ptr -> Int value (unsafe only)", ALL),
    # kernel surface (interp fakes PMM hosted; xkernel is real)
    "ticks": ("ticks()", "ms ticks hosted, 100Hz timer on kernel", NO_XBUILD),
    "readkey": ("readkey()", "stdin char hosted, last key or Null on kernel",
                NO_XBUILD),
    "pmm_alloc": ("pmm_alloc(npages)", "allocate physical pages", NO_XBUILD),
    "pmm_total": ("pmm_total()", "total pages (xkernel only)", {"xkernel"}),
    "pmm_free": ("pmm_free()", "free pages", NO_XBUILD),
    "meminfo": ("meminfo()", "dict total/free/page (hosted only)", HOSTED),
}
