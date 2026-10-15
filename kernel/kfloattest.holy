fails = 0
def expect(label, got, want):
  global fails
  if got == want:
    print "ok", label
    return
  print "FAIL", label, got, want
  fails = fails + 1
expect("lit", 1.5 + 2.5, 4.0)
expect("mixed", 1 + 2.5, 3.5)
expect("div", 7.5 / 2, 3.75)
expect("mul", 2.0 * 3.0, 6.0)
expect("mod", 7.5 % 2.0, 1.5)
expect("mod neg", (0 - 1.5) % 2.0, 0.5)
expect("mod neg divisor", 1.5 % (0 - 2.0), 0 - 0.5)
expect("negzero", 0 - 0.0, 0.0)
expect("inf", float("inf") == float("inf"), true)
expect("nan self", float("nan") == float("nan"), false)
expect("nan lt", float("nan") < 2.0, false)
expect("shortest 0.5", str(0.5), "0.5")
expect("shortest 0.1", str(0.1), "0.1")
expect("pi", str(3.141592653589793), "3.141592653589793")
expect("big", str(float("1.152921504606847e+18")), "1.152921504606847e+18")
expect("tiny", str(float("5e-324")), "5e-324")
expect("huge", str(float("1.7976931348623157e+308")), "1.7976931348623157e+308")
expect("exp fmt", str(float("1e-08")), "1e-08")
expect("parse", float("1.5"), 1.5)
expect("parse exp", str(float("6.290184345309701e-235")), "6.290184345309701e-235")
expect("parse trim", float("  2.5  "), 2.5)
expect("parse mantissa", str(float("5.896816288783659e+166")), "5.896816288783659e+166")
expect("int trunc", int(3.99), 3)
expect("int neg trunc", int(0 - 3.99), 0 - 3)
expect("int str", int("0x2a"), 42)
expect("float int", float(7), 7.0)
expect("float bool", float(true), 1.0)
expect("list", str([1.5, 2.5]), "[1.5, 2.5]")
expect("dict", str({"pi": 3.14}), "{pi: 3.14}")
if fails == 0:
  print "kfloattest ok"
else:
  print "kfloattest fails", fails
