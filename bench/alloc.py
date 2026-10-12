i=0
n=0
while i<5000000:
    s="abc"+str(i)
    n+=len(s)
    i+=1
print(n)
