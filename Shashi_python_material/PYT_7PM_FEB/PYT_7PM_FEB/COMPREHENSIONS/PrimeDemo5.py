




#comprehensions
#Syn: [ <exp> for variable in iterable if test ]
#Syn: ( <exp> for variable in iterable )
#Syn: { <exp> for variable in iterable }
#Syn  { <exp> for variable in iterable } exp should be in the form k and v pairs

lst=["ramesh","roja","srija","manas","madhu"]
print("List ",lst)


lst2=[i for i in lst if i[-2] in "jJ"]
print("Result is : ",lst2)











