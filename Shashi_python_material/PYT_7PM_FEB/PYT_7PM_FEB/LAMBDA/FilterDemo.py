




#filter(function or None,iterable) -> filter object
lst=[1,2,3,4,5,6,7,8,9,10]
f=filter( lambda x: x%2==0 , lst)
#print("filter Object : ",f)
lst2=list(f)
print("Result is : ",lst2)

print( tuple(filter( lambda x: x%2==0, [4,5,6,7,8,9,10] )) )
