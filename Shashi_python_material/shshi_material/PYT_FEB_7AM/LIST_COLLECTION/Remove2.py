#L.append(item)
#L.insert(index,item)
#L.extend(iterable)
#L.copy( ) -> shallow copy

#L.index(item[,start,end]) -> int
#Str.count(sub[,start,end]) -> int
#L.count(item) -> int

#L.pop(index=-1) -> item
#L.remove(item) 

#        0   1   2    3    4   5    6
lst=[10,20,30,40,50,60,30]
print("List : ",lst)

item=eval(input("enter an item  " ))
lst2=[]

for i in lst:
    if i!=item:
        lst2.append(i)

lst1=lst2
del lst2
print("After Deleting : ",lst1)
    








