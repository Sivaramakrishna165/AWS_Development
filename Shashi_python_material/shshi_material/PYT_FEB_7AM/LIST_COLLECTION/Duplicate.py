#L.append(item)
#L.insert(index,item)
#L.extend(iterable)
#L.copy( ) -> shallow copy

#L.index(item[,start,end]) -> int
#Str.count(sub[,start,end]) -> int
#L.count(item) -> int

#L.pop(index=-1) -> item
#L.remove(item) 

#        0   1   2    3    4   
lst=[10,30,20,30,60,30]
print("List : ",lst)

lst2=[]

for i in lst:
    if i not in lst2:
        lst2.append(i)

lst=lst2
del lst2
print("Unique Element : ",lst)











