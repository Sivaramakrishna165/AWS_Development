#L.append(item)
#L.insert(index,item)
#L.extend(iterable)
#L.copy( ) -> shallow copy
#L.index(item[,start,end]) -> int 

#        0   1   2    3    4   5    6
lst=[10,20,30,40,50,60,30]
print("List : ",lst)

print("30 in lst ? : ",30 in lst)
pos=lst.index(30)
print("Found @ : ",pos)

pos=lst.index(30,3,7)
print("Found @ : ",pos)
