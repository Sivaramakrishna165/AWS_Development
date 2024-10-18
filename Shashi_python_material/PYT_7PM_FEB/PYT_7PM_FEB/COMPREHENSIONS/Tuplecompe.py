




#comprehensions
#Syn: [ <exp> for variable in iterable if test ]
#Syn: ( <exp> for variable in iterable if test)
#Syn: { <exp> for variable in iterable  if test }
#Syn  { <exp> for variable in iterable } exp should be in the form k and v pairs

g=(i for i in range(1,11) if i%3==0)
print("type is : ",type(g))
print("tuple object : ",g)
t=tuple(g)
print("Result is : ",t)


    







