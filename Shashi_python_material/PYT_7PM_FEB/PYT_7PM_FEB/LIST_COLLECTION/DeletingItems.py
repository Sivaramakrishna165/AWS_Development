



#L.pop([index]) -> item | default index=-1
#L.remove( )
#L.clear( )

#       0    1    2   3   4   5
lst=[10,20,30,40,5,10]
print("List : ",lst)

item=lst.pop()
print("Deleted Item is : ",item)
print("List after pop : ",lst)

item=lst.pop(20)
print("Deleted Item is : ",item)
print("List After Pop : ",lst)
