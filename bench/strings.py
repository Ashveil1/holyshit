parts=[]
i=0
while i<3000000:
    parts.append(str(i)); i+=1
t=",".join(parts)
print(len(t)); print(len(t.split(",")))
