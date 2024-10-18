
#L.append(item) 
#L.insert(int,item)
#L.extend(iterable)

l1=["A","B","C"]
l2=[10,20,30]

print("L1 : ",l1)
print("L2 : ",l2)

l3=l1+l2
print("Result : ",l3)
print("L1 : ",l1)
print("========================")

l1.extend(l2)  #l1=l1+l2
print("Result is : ",l1)



