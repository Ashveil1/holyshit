n = int(argv()[0])
ok = n >= 2
i = 2
while ok and i * i <= n:
  if n % i == 0:
    ok = false
  i = i + 1
print ok
