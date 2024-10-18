




#comprehensions
#Syn: [ <exp> for variable in iterable if test ]
#Syn: ( <exp> for variable in iterable )
#Syn: { <exp> for variable in iterable }
#Syn  { <exp> for variable in iterable } exp should be in the form k and v pairs

lst=["ramesh","roja","srija","manas","madhu"]
print("List ",lst)

#filter(func,iterable) -> filter object | iterable
lr=list( filter( lambda x: len(x)==5, lst) )
print("Result is : ",lr)

lst2=[i for i in lst if len(i)==5] 
print("List2 : ",lst2)







