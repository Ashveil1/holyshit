# Self-hosted lexer: the hs lexer written in hs. Prints one token per line:
#   KIND<TAB>value<TAB>line
# and must match `python3 selfhost/dump_lex.py FILE` byte for byte.
# Errors print "error: msg at line N" and exit 1, like interp.

DIG = "0123456789"
HEXD = "0123456789abcdefABCDEF"
IDS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
OPS2 = ["<<", ">>", "==", "!=", "<=", ">="]
OPS1 = "+-*/%<>=&|^~(){}[],:."

def fail(msg, ln):
  print "error: " + msg + " at line " + str(ln)
  exit_now()

def exit_now():
  # no exit builtin: raise to stop with a non-zero status
  raise "lex failed"

def esc_out(s):
  out = ""
  i = 0
  while i < len(s):
    c = s[i]
    if c == "\\":
      out = out + "\\\\"
    elif c == "\n":
      out = out + "\\n"
    elif c == "\t":
      out = out + "\\t"
    elif c == "\r":
      out = out + "\\r"
    elif c == "\0":
      out = out + "\\0"
    else:
      out = out + c
    i = i + 1
  return out

def unesc(lit):
  s = lit[1:len(lit) - 1]
  out = ""
  i = 0
  while i < len(s):
    if s[i] == "\\" and i + 1 < len(s):
      n = s[i + 1]
      if n == "n":
        out = out + "\n"
      elif n == "t":
        out = out + "\t"
      elif n == "r":
        out = out + "\r"
      elif n == "0":
        out = out + "\0"
      else:
        out = out + n
      i = i + 2
    else:
      out = out + s[i]
      i = i + 1
  return out

def emit(kind, v, ln):
  print kind + "\t" + v + "\t" + str(ln)

def digits_end(c, j):
  while j < len(c) and c[j] in DIG:
    j = j + 1
  return j

def exp_end(c, j):
  # optional exponent at j: returns the new end (or j when none)
  if j < len(c) and (c[j] == "e" or c[j] == "E"):
    k = j + 1
    if k < len(c) and (c[k] == "+" or c[k] == "-"):
      k = k + 1
    if k < len(c) and c[k] in DIG:
      return digits_end(c, k)
  return j

def lex_line(c, ln):
  j = 0
  while j < len(c):
    ch = c[j]
    if c[j:j + 2] == "//" or ch == "#":
      return 0
    if ch == " " or ch == "\t":
      j = j + 1
    elif ch == "f" and j + 1 < len(c) and c[j + 1] == "\"":
      k = j + 2
      while k < len(c) and c[k] != "\"":
        if c[k] == "\\":
          k = k + 1
        k = k + 1
      if k >= len(c):
        fail("bad character " + "'" + ch + "'", ln)
      emit("FSTR", esc_out(c[j + 2:k]), ln)
      j = k + 1
    elif ch == "\"":
      k = j + 1
      while k < len(c) and c[k] != "\"":
        if c[k] == "\\":
          k = k + 1
        k = k + 1
      if k >= len(c):
        fail("bad character " + "'" + ch + "'", ln)
      emit("STR", esc_out(unesc(c[j:k + 1])), ln)
      j = k + 1
    elif ch in DIG or (ch == "." and j + 1 < len(c) and c[j + 1] in DIG):
      if ch == "0" and j + 2 < len(c) + 0 and (c[j + 1] == "x" or c[j + 1] == "X") and c[j + 2] in HEXD:
        k = j + 2
        while k < len(c) and c[k] in HEXD:
          k = k + 1
        emit("NUM", c[j:k], ln)
        j = k
      else:
        k = digits_end(c, j)
        isf = false
        if k < len(c) and c[k] == ".":
          isf = true
          k = digits_end(c, k + 1)
          k = exp_end(c, k)
        else:
          e = exp_end(c, k)
          if e > k:
            isf = true
            k = e
        emit("NUM", c[j:k], ln)
        j = k
    elif ch in IDS:
      k = j
      while k < len(c) and (c[k] in IDS or c[k] in DIG):
        k = k + 1
      w = c[j:k]
      if w == "module":
        fail("'module' is reserved for future use", ln)
      emit("ID", w, ln)
      j = k
    elif c[j:j + 2] in OPS2:
      emit("OP", c[j:j + 2], ln)
      j = j + 2
    elif ch in OPS1:
      emit("OP", ch, ln)
      j = j + 1
    else:
      fail("bad character " + "'" + ch + "'", ln)

def strip_cr(s):
  if len(s) > 0 and s[len(s) - 1] == "\r":
    return s[0:len(s) - 1]
  return s

def blank_or_comment(s):
  i = 0
  while i < len(s) and (s[i] == " " or s[i] == "\t" or s[i] == "\n" or s[i] == "\r"):
    i = i + 1
  if i >= len(s):
    return true
  return s[i] == "#" or s[i:i + 2] == "//"

src = read_text(argv()[0])
lines = split(src, "\n")
stack = [0]
ln = 0
n = 0
while n < len(lines):
  ln = n + 1
  line = strip_cr(lines[n])
  n = n + 1
  if blank_or_comment(line):
    continue
  i = 0
  while i < len(line) and line[i] == " ":
    i = i + 1
  if i < len(line) and line[i] == "\t":
    fail("tabs not allowed, use spaces", ln)
  top = stack[len(stack) - 1]
  if i > top:
    append(stack, i)
    emit("INDENT", "", ln)
  elif i < top:
    while len(stack) > 0 and i < stack[len(stack) - 1]:
      stack = stack[0:len(stack) - 1]
      emit("DEDENT", "", ln)
    if len(stack) == 0 or i != stack[len(stack) - 1]:
      fail("inconsistent indent", ln)
  lex_line(line[i:len(line)], ln)
  emit("NEWLINE", "", ln)
while len(stack) > 1:
  stack = stack[0:len(stack) - 1]
  emit("DEDENT", "", ln)
emit("EOF", "", ln)
