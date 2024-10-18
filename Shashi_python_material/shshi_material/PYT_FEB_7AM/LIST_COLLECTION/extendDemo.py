#L.copy() -> shallow copy
#L.append(item)
#L.insert(index,item)
#L.extend(iterable) 

#       0    1     2
lst1=[10,20,30]
print("List 1 : ",lst1)

lst2=["a","b","c"]
print("List 2 : ",lst2)

lst3=lst1+lst2 #list concatenation
print("Result is : ",lst3)

lst1.extend(lst2) #lst1=lst1+lst2
print("Result is : ",lst1)





