def enc(v):
  return json_str(v)
def dec(s):
  return json_str(json_parse(s))
def attempt(label, f):
  try:
    v = f()
    print label, "ok", v
  except as e:
    print label, "err", e
def e1():
  return json_str([1, 2.5, true, false, null, "hi", {"a": 1, "b": [2]}])
def e2():
  return json_str("quote \" backslash \\ slash / tab\there")
def e3():
  return json_str("héllo → ✓ 😀")
def e4():
  return json_str({"z": 1, "a": 2, "m": [1, {"k": null}]})
def e5():
  return json_str(1.5)
def e6():
  return json_str(0.0001)
def d1():
  return dec("1")
def d2():
  return dec("[1, 2, 3]")
def d3():
  return dec("{\"a\": [1, null, true], \"b\": {\"c\": \"x\"}}")
def d4():
  return dec("  -2.5e3  ")
def d5():
  return dec("\"\\u00e9\\ud83d\\ude00\"")
def d6():
  return dec("[]")
def d7():
  return dec("{}")
def d8():
  return dec("\"a\\n\\t\\\\\\/\"")
def d9():
  return dec("1e400")
def d10():
  return dec("0.0")
def x1():
  return json_parse("bad")
def x2():
  return json_parse("[1,2,]")
def x3():
  return json_parse("{\"a\":1,}")
def x4():
  return json_parse("1 2")
def x5():
  return json_parse("[1 2]")
def x6():
  return json_parse("\"abc")
def x7():
  return json_parse("{1: 2}")
def x8():
  return json_str(float("inf"))
def x9():
  return json_str(float("nan"))
def x10():
  return json_parse("")
attempt("enc-mixed", e1)
attempt("enc-escapes", e2)
attempt("enc-utf8", e3)
attempt("enc-order", e4)
attempt("enc-float", e5)
attempt("enc-small", e6)
attempt("dec-int", d1)
attempt("dec-list", d2)
attempt("dec-nested", d3)
attempt("dec-exp", d4)
attempt("dec-unicode", d5)
attempt("dec-empty-list", d6)
attempt("dec-empty-obj", d7)
attempt("dec-escapes", d8)
attempt("dec-overflow", d9)
attempt("dec-zero", d10)
attempt("err-word", x1)
attempt("err-trail-arr", x2)
attempt("err-trail-obj", x3)
attempt("err-extra", x4)
attempt("err-comma", x5)
attempt("err-unterm", x6)
attempt("err-key", x7)
attempt("err-inf", x8)
attempt("err-nan", x9)
attempt("err-empty", x10)
