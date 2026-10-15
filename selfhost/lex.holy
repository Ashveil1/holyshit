# Self-hosted lexer driver: prints one token per line
#   KIND<TAB>value<TAB>line
# and must match `python3 selfhost/dump_lex.py FILE` byte for byte.
# Errors print "error: msg at line N" and exit 1, like interp.
import lexlib

def tsv(s):
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

try:
  toks = lexlib.lex(read_text(argv()[0]))
except as e:
  print "error: " + e
  raise "lex failed"
for t in toks:
  v = t[1]
  if t[0] == "STR" or t[0] == "FSTR":
    v = tsv(v)
  print t[0] + "\t" + v + "\t" + str(t[2])
