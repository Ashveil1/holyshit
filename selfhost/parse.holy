# Self-hosted parser driver: prints the AST as JSON, which must equal
# `python3 selfhost/dump_parse.py FILE` (interp.parse_program).
import parselib

try:
  print json_str(parselib.parse(read_text(argv()[0])))
except as e:
  print "error: " + parselib.strip_raise(e)
  raise "parse failed"
