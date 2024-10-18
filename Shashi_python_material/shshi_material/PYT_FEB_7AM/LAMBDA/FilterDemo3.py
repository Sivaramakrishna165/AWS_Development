




#filter(function or None,iterable) -> filter object | iterable
lst=["anu","manas","madhu","raj","Sudha","MamathA"]
print("List : ",lst)

lst3=list( filter( lambda x: len(x)==3 , lst))
print("Result is : ",lst3)

lsta=list( filter(lambda x: x.endswith('a') or x.endswith('A'), lst) )
print("Result is : ",lsta)

t=list( filter(lambda x: x[-1] in ['a','A'] , lst) )
print("Result is : ",t)





