#L.append(item)
#L.insert(index,item)
#L.extend(iterable)
#L.copy( ) -> shallow copy

#L.index(item[,start,end]) -> int
#Str.count(sub[,start,end]) -> int
#L.count(item) -> int

#L.pop(index=-1) -> item

#        0   1   2    3    4   5    6
lst=[10,20,30,40,50,60,30]
print("List : ",lst)

item=lst.pop()
print("Deleted item is : ",item)

item=lst.pop(3)
print("Deleted item is : ",item)

print("List : ",lst)














