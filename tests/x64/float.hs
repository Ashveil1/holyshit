print 0.0, -0.0, 1.0, -1.0
print 0.5, 0.1, 2.675, 3.141592653589793
print float(7), float(-3), float(true), float(false)
print int(3.99), int(-3.99), int("  42  "), int("0x2a")
print float("5e-324"), float("1.7976931348623157e+308")
print float("1e-08"), float("1e16"), float("inf"), float("nan")
print 1.5 + 2, 3 + 1.5, 7.5 - 2.5, 1.5 * 2, 7.5 / 2
print 7.5 % 2.0, -1.5 % 2.0, 1.5 % -2.0
print 2.5 < 3, 3 < 2.5, 2.5 <= 2.5, 3.0 > 2.9
print 0.0 == -0.0, 1.0 == true, 0.0 == false
print float("nan") == float("nan"), float("nan") < 2.0
print [1.5, 2.5], {"pi": 3.14}
print str(float("6.290184345309701e-235"))
print float("5.896816288783659e+166")
# int() as an index operand: every conversion path has to keep the stack even
s = "0123456789abcdef"
print s[int(3)], s[int(2.9)], s[int("10")]
print s[int(0.0) + int(1)], s[int(true)]
