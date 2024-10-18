




#filter(func or None , iterables ) -> filter object | iterable
lst=["anu","roja","srija","KhannA","Manas"]
print("List : ",lst)

s=set(filter(lambda x: len(x)==3 ,lst) )
print("names with 3 char : ",s)
print("===================================")

t=tuple( filter(lambda x: x[-1]=='a' or x[-1]=='A', lst) )
print("Result is : ",t)

print("===================================")
t=tuple( filter( lambda x: x[-1] in "aA" ,lst ) )
print("Result is : ",t)

print("===================================")
s=set(filter( lambda x: x.endswith('a') or x.endswith('A') , lst ))
print("Result is : ",s)





