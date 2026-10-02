# std.str — string helpers (pure hs)
def _is_space(c):
  return c == " " or c == "\t" or c == "\n" or c == "\r"

def trim(s):
  i = 0
  while i < len(s) and _is_space(s[i]):
    i = i + 1
  j = len(s)
  while j > i and _is_space(s[j - 1]):
    j = j - 1
  return s[i:j]

def pad_left(s, w):
  while len(s) < w:
    s = " " + s
  return s

def pad_right(s, w):
  while len(s) < w:
    s = s + " "
  return s

def starts_with(s, pre):
  return s[:len(pre)] == pre

def ends_with(s, suf):
  if len(suf) == 0:
    return true
  return s[len(s) - len(suf):] == suf

def lines(s):
  return split(s, "\n")
