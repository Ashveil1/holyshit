s = argv()[0]
i = 0
j = len(s) - 1
ok = true
while i < j:
  if s[i] != s[j]:
    ok = false
  i = i + 1
  j = j - 1
print ok
