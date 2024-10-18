
l1=[10,20,30]
print("L1 : ",l1)
l2=l1
print("L2 : ",l2)

l1[1]=22
print("After Modification ")
print("l1 : ",l1)
print("l2 : ",l2)
print("======================")

#L.copy() -> shallow copy list
x=[10,20,30]
print("List x : ",x)

y=x.copy()
print("List y : ",y)

x[1]=99
print("After Modification ")
print("List x : ",x)
print("List y : ",y)














