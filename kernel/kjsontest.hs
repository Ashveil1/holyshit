fails = 0
def expect(label, got, want):
  global fails
  if got == want:
    print "ok", label
    return
  print "FAIL", label, got, want
  fails = fails + 1
def bad_bracket():
  return json_parse("[")
def bad_trailing():
  return json_parse("1 2")
def bad_quoted():
  return json_str(float("inf"))
def bad_nan():
  return json_str(float("nan"))
def attempt(label, f):
  try:
    v = f()
    print label, "ok", v
  except as e:
    print label, "err", e
expect("enc list", json_str([1, 2.5, true, null, "hi"]), "[1, 2.5, true, null, \"hi\"]")
expect("enc obj", json_str({"a": 1, "b": [2]}), "{\"a\": 1, \"b\": [2]}")
expect("enc empty", json_str([]), "[]")
expect("enc quote", json_str("a\"b\\c"), "\"a\\\"b\\\\c\"")
expect("enc nl", json_str("a\nb"), "\"a\\nb\"")
expect("enc num", json_str(1.5), "1.5")
expect("enc utf8", json_str("é→"), "\"\\u00e9\\u2192\"")
d = json_parse("{\"n\": [1, 2.5, true, null, \"s\"]}")
expect("dec keys", len(d), 1)
expect("dec text", json_str(d), "{\"n\": [1, 2.5, true, null, \"s\"]}")
expect("dec int", json_parse("42"), 42)
expect("dec float", json_parse("2.5"), 2.5)
expect("dec str", json_parse("\"x\""), "x")
expect("dec bool", json_parse("true"), true)
expect("dec null", json_parse("null"), null)
expect("dec nested", len(json_parse("[1, [2, [3]]]")), 2)
expect("dec deep", json_str(json_parse("[1, [2, [3]]]")), "[1, [2, [3]]]")
expect("dec escape", json_parse("\"\\u00e9\""), "é")
expect("dec surrogate", json_parse("\"\\ud83d\\ude00\""), "😀")
expect("dec spaces", json_parse("  7  "), 7)
expect("dec obj", json_str(json_parse("{}")), "{}")
attempt("bad-bracket", bad_bracket)
attempt("bad-trailing", bad_trailing)
attempt("bad-inf", bad_quoted)
attempt("bad-nan", bad_nan)
if fails == 0:
  print "kjsontest ok"
else:
  print "kjsontest fails", fails
