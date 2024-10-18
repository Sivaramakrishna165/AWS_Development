




#filter(function or None,iterable) -> filter object | iterable
lst=[1,2,3,4,5]
print("Data : ",lst)

f=filter( lambda x:  x%2==0 , lst )
print("Filter Object : ",f)
lst=list(f)
print("Result is : ",lst)
