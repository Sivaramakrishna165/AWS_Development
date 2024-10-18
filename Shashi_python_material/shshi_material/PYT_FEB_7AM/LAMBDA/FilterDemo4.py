



#filter(function or None,iterable) -> filter object
lst=[10,0,12.12,0.0,"","Ramesh",True,234,23]
print("list ",lst)

lr=list( filter(None ,lst) )
print("Result is : ",lr)

lint=list( filter( lambda x: isinstance(x,int) ,lst) )
print("Result is int : ",lint)
