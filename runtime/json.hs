# JSON support for the x64 backend.
#
# x64gen compiles this file into the image as a private module (`<json>`)
# whenever the program mentions json_parse / json_str / json_load /
# json_save. The four builtins are the only supported interface, exactly
# like interp.py (which calls Python's `json`); the entry points here return
# the internal [error, value] convention, not a JSON value.
#
# One hook exists for the backend's copy only -- `type_name(x)`, compiled
# straight to the x_tname runtime routine. A hand-written `import
# runtime.json` gets a second, independent copy without that hook, so
# anything reaching `type_name` (js_str_of, js_encode, js_decode, ...) fails
# to compile with "unknown variable 'type_name'"; only the byte helpers work
# there. Not an API, just something that happens to sit in the repo.
#
# Every entry point returns a 2-element List:
#   [null, value]        success
#   ["<message>", null]  failure -- the message interp would report, so the
#                        builtin wrapper can raise it at the caller's line
#
# Strings are handled as bytes (an x64 Str is a UTF-8 buffer): `s[i]` is one
# byte and `len(s)` is a byte count. Multi-byte sequences are decoded to
# code points before being escaped, so the output matches CPython for the
# same logical string.
#
# Two rules shape the layout: x64 resolves module-level names statically, so
# a helper must be defined *before* its callers, and there is no mutual
# recursion. The decoder therefore keeps every container inside one
# `js_value` that only ever calls itself.
#
# Recursion is bounded at 200 like interp (_JSON_DEPTH).

# ---------- byte access ----------
#
# An x64 Str is a UTF-8 byte buffer: `len(s)` counts bytes and `s[i]` is the
# byte at i (as a one-byte Str). Comparisons need the numeric value, and hs
# has no chr/ord, so read it straight out of the payload with load8. This
# file only ever runs on x64, where that is exactly the byte.

def byte_at(s, i):
  unsafe:
    Ptr p = as_ptr(s)
    return load8(p + 16 + i)

def js_at(s, i, n):
  # the byte at i, or -1 once the string ends (x64 `and`/`or` do not
  # short-circuit, so every bound test has to be safe on its own)
  if i >= n:
    return -1
  return byte_at(s, i)

# ---------- byte -> a one-byte Str (hs has no chr) ----------
#
# An x64 Str is a UTF-8 byte buffer, so building a Str from a byte value is
# the one thing the subset cannot spell directly. alloc + store8 + read_mem
# is the byte-level round trip it does offer: write the byte into a fresh
# cell, then read that address back as a Str.

def js_cell(b):
  unsafe:
    Ptr p = alloc(8)
    store8(p, b)
    return as_int(p)

def js_chr(b):
  return read_mem(js_cell(b), 1)

HEX = "0123456789abcdef"

def pow16(k):
  if k == 3:
    return 4096
  if k == 2:
    return 256
  if k == 1:
    return 16
  return 1

def pow64(k):
  if k == 2:
    return 4096
  if k == 1:
    return 64
  return 1

def js_hex4(n):
  s = ""
  k = 3
  while k >= 0:
    s = s + HEX[int(n / pow16(k)) % 16]
    k = k - 1
  return s

def js_u16(cp):
  return "\\u" + js_hex4(cp)

def js_codepoint(cp):
  # one code point as JSON text: BMP directly, above it a surrogate pair
  if cp < 0x10000:
    return js_u16(cp)
  v = cp - 0x10000
  return js_u16(0xD800 + int(v / 1024)) + js_u16(0xDC00 + v % 1024)

# ---------- json_str: encode ----------

def js_quote(s):
  out = "\""
  i = 0
  n = len(s)
  while i < n:
    b = byte_at(s, i)
    if b == 34:
      out = out + "\\\""
    elif b == 92:
      out = out + "\\\\"
    elif b == 10:
      out = out + "\\n"
    elif b == 13:
      out = out + "\\r"
    elif b == 9:
      out = out + "\\t"
    elif b == 8:
      out = out + "\\b"
    elif b == 12:
      out = out + "\\f"
    elif b < 32 or b == 127:
      out = out + js_u16(b)
    elif b < 128:
      out = out + s[i]
    else:
      # multi-byte UTF-8: decode to a code point, then escape it. i ends on
      # the last continuation byte so the loop tail steps past the sequence.
      need = 1
      cp = (b - 192) * 64
      if b >= 240:
        cp = (b - 240) * 262144
        need = 3
      elif b >= 224:
        cp = (b - 224) * 4096
        need = 2
      k = 0
      while k < need:
        i = i + 1
        cp = cp + (byte_at(s, i) - 128) * pow64(need - 1 - k)
        k = k + 1
      out = out + js_codepoint(cp)
    i = i + 1
  return out + "\""

def js_nan_inf(v):
  # json.dumps(allow_nan=False) refuses these, with the value in the text
  t = str(v)
  if t == "inf" or t == "-inf" or t == "nan":
    return ["json_str failed: Out of range float values are not JSON compliant: " + t, null]
  return [null, t]

def js_str_of(v, depth):
  if depth > 200:
    return ["json too deeply nested", null]
  t = type_name(v)
  if t == "Null":
    return [null, "null"]
  if t == "Bool":
    if v:
      return [null, "true"]
    return [null, "false"]
  if t == "Int":
    return [null, str(v)]
  if t == "Float":
    return js_nan_inf(v)
  if t == "Str":
    return [null, js_quote(v)]
  if t == "List":
    parts = []
    i = 0
    n = len(v)
    while i < n:
      if i > 0:
        append(parts, ", ")
      r = js_str_of(v[i], depth + 1)
      if r[0] != null:
        return r
      append(parts, r[1])
      i = i + 1
    return [null, "[" + join("", parts) + "]"]
  if t == "Dict":
    parts = []
    first = true
    for k in v:
      if first:
        first = false
      else:
        append(parts, ", ")
      append(parts, js_quote(k))
      append(parts, ": ")
      r = js_str_of(v[k], depth + 1)
      if r[0] != null:
        return r
      append(parts, r[1])
    return [null, "{" + join("", parts) + "}"]
  return ["not JSON-serializable: " + t, null]

def js_encode(v):
  return js_str_of(v, 0)

# ---------- json_parse: decode ----------

def js_ws(c):
  return c == 32 or c == 9 or c == 10 or c == 13

def js_skip(s, i):
  n = len(s)
  while js_at(s, i, n) != -1 and js_ws(js_at(s, i, n)):
    i = i + 1
  return i

def js_hexval(c):
  if c >= 48 and c <= 57:
    return c - 48
  if c >= 97 and c <= 102:
    return c - 87
  if c >= 65 and c <= 70:
    return c - 55
  return -1

def js_bad(msg):
  return [msg, null]

def js_lit(s, i, word):
  # match a bare word at i; returns the index after it or -1
  k = 0
  n = len(word)
  m = len(s)
  while k < n:
    if i + k >= m:
      return -1
    if s[i + k] != word[k]:
      return -1
    k = k + 1
  return i + n

def js_utf8(out, cp):
  # append the UTF-8 bytes of one code point (append mutates in place)
  if cp < 0x80:
    append(out, js_chr(cp))
    return
  if cp < 0x800:
    append(out, js_chr(192 + int(cp / 64)) + js_chr(128 + cp % 64))
    return
  if cp < 0x10000:
    append(out, js_chr(224 + int(cp / 4096)) + js_chr(128 + int(cp / 64 % 64)) + js_chr(128 + cp % 64))
    return
  # above the BMP: four bytes, not a surrogate pair
  append(out, js_chr(240 + int(cp / 262144)))
  append(out, js_chr(128 + int(cp / 4096 % 64)))
  append(out, js_chr(128 + int(cp / 64 % 64)))
  append(out, js_chr(128 + cp % 64))

def js_is(s, i, n, b):
  # 1 when byte i exists and equals b
  if js_at(s, i, n) == b:
    return 1
  return 0

def js_string(s, i):
  # s[i] is '"'; returns [null, [Str, next]] or a failure
  out = []
  i = i + 1
  n = len(s)
  while i < n:
    b = byte_at(s, i)
    if b == 34:
      return [null, [join("", out), i + 1]]
    if b == 92:
      if i + 1 >= n:
        return js_bad("Unterminated string starting at")
      e = byte_at(s, i + 1)
      if e == 34:
        append(out, "\"")
      elif e == 92:
        append(out, "\\")
      elif e == 47:
        append(out, "/")
      elif e == 98:
        append(out, js_chr(8))
      elif e == 102:
        append(out, js_chr(12))
      elif e == 110:
        append(out, "\n")
      elif e == 114:
        append(out, "\r")
      elif e == 116:
        append(out, "\t")
      elif e == 117:
        cp = 0
        k = 0
        while k < 4:
          if i + 2 + k >= n:
            return js_bad("Invalid \\uXXXX escape")
          d = js_hexval(byte_at(s, i + 2 + k))
          if d < 0:
            return js_bad("Invalid \\uXXXX escape")
          cp = cp * 16 + d
          k = k + 1
        j = i + 6                 # just past this escape
        # a high surrogate followed by \uDC00-\uDFFF is one astral code point
        if cp >= 55296 and cp < 56320 and js_is(s, j, n, 92) and js_is(s, j + 1, n, 117):
          lo = 0
          k = 0
          ok = true
          while k < 4:
            d = -1
            if j + 2 + k < n:
              d = js_hexval(byte_at(s, j + 2 + k))
            if d < 0:
              ok = false
            lo = lo * 16 + d
            k = k + 1
          if ok and lo >= 56320 and lo < 57344:
            cp = 65536 + (cp - 55296) * 1024 + lo - 56320
            j = j + 6
        js_utf8(out, cp)
        i = j - 2                 # the shared `i = i + 2` lands on j
      else:
        return js_bad("Invalid \\escape")
      i = i + 2
      continue
    if b < 32:
      return js_bad("Invalid control character at")
    append(out, s[i])
    i = i + 1
  return js_bad("Unterminated string starting at")

def js_number(s, i):
  # -?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][-+]?[0-9]+)? with CPython's messages
  n = len(s)
  start = i
  if byte_at(s, i) == 45:
    i = i + 1
    if i >= n or byte_at(s, i) < 48 or byte_at(s, i) > 57:
      return js_bad("Expecting value")
  if byte_at(s, i) == 48:
    i = i + 1
  else:
    while js_at(s, i, n) >= 48 and js_at(s, i, n) <= 57:
      i = i + 1
  isfloat = false
  if js_is(s, i, n, 46):
    j = i + 1
    if js_at(s, j, n) >= 48 and js_at(s, j, n) <= 57:
      isfloat = true
      i = j
      while js_at(s, i, n) >= 48 and js_at(s, i, n) <= 57:
        i = i + 1
  if js_is(s, i, n, 101) or js_is(s, i, n, 69):
    j = i + 1
    if js_is(s, j, n, 43) or js_is(s, j, n, 45):
      j = j + 1
    if js_at(s, j, n) >= 48 and js_at(s, j, n) <= 57:
      isfloat = true
      i = j
      while js_at(s, i, n) >= 48 and js_at(s, i, n) <= 57:
        i = i + 1
  text = s[start:i]
  if isfloat:
    return [null, [float(text), i]]
  return [null, [int(text), i]]

def js_value(s, i, depth):
  # one complete JSON value at i (whitespace already skipped on entry)
  if depth > 200:
    return js_bad("json too deeply nested")
  n = len(s)
  if i >= n:
    return js_bad("Expecting value")
  c = byte_at(s, i)
  if c == 34:
    return js_string(s, i)
  if c == 116:
    j = js_lit(s, i, "true")
    if j < 0:
      return js_bad("Expecting value")
    return [null, [true, j]]
  if c == 102:
    j = js_lit(s, i, "false")
    if j < 0:
      return js_bad("Expecting value")
    return [null, [false, j]]
  if c == 110:
    j = js_lit(s, i, "null")
    if j < 0:
      return js_bad("Expecting value")
    return [null, [null, j]]
  if c == 45 or c >= 48 and c <= 57:
    return js_number(s, i)
  # a container: '[' builds a List, '{' builds a Dict, in this same frame
  isobj = c == 123
  if not isobj and c != 91:
    return js_bad("Expecting value")
  out = []
  if isobj:
    out = {}
  i = js_skip(s, i + 1)
  closer = 125
  if not isobj:
    closer = 93
  if js_is(s, i, n, closer):
    return [null, [out, i + 1]]
  while true:
    if isobj:
      i = js_skip(s, i)
      if not js_is(s, i, n, 34):
        return js_bad("Expecting property name enclosed in double quotes")
      r = js_string(s, i)
      if r[0] != null:
        return r
      key = r[1][0]
      i = js_skip(s, r[1][1])
      if not js_is(s, i, n, 58):
        return js_bad("Expecting ':' delimiter")
      i = i + 1
    i = js_skip(s, i)
    r = js_value(s, i, depth + 1)
    if r[0] != null:
      return r
    if isobj:
      out[key] = r[1][0]
    else:
      append(out, r[1][0])
    i = js_skip(s, r[1][1])
    # at the end of the text the closer and comma checks both fail, which is
    # how CPython reports a truncated array/object
    if js_is(s, i, n, closer):
      return [null, [out, i + 1]]
    if not js_is(s, i, n, 44):
      return js_bad("Expecting ',' delimiter")
    i = js_skip(s, i + 1)
    if js_is(s, i, n, closer):
      if isobj:
        return js_bad("Illegal trailing comma before end of object")
      return js_bad("Illegal trailing comma before end of array")

def js_decode(s):
  # js_value reports [err, [value, next]]; the entry point hands the
  # builtin wrapper the value alone
  r = js_value(s, js_skip(s, 0), 0)
  if r[0] != null:
    return r
  i = js_skip(s, r[1][1])
  if i < len(s):
    return js_bad("Extra data")
  return [null, r[1][0]]