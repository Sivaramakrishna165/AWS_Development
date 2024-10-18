lst=[30,40,20,0,5,0]

lst2=[]
lst3=[]

for i in lst:
    if i==0:
        lst2.append(i)
    else:
        lst3.append(i)

lst3.extend(lst2)
print(lst3)
