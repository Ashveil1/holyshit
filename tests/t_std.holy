import std.str
import std.list

print std.str.trim("  hi  ")
print std.str.pad_left("7", 3)
print std.str.pad_right("7", 3)
print std.str.starts_with("hello", "he")
print std.str.ends_with("hello", "lo")
print std.str.lines("a\nb")

def mul(a):
  def by(x):
    return a * x
  return by

print std.list.map(mul(3), [1, 2, 3])

def is_even(x):
  return x % 2 == 0

print std.list.filter(is_even, [1, 2, 3, 4])

def add(a, b):
  return a + b

print std.list.fold(add, 0, [1, 2, 3, 4])
print std.list.any(is_even, [1, 3])
print std.list.all(is_even, [2, 4])
