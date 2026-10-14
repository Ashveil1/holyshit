def caught():
  try:
    raise "caught"
  except as e:
    return 1
s = 0
for i in range(300):
  s = s + caught()
print s
