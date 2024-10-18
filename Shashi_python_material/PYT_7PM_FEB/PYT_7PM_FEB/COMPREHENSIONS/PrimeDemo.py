




#comprehensions
#Syn: [ <exp> for variable in iterable if test ]
#Syn: ( <exp> for variable in iterable )
#Syn: { <exp> for variable in iterable }
#Syn  { <exp> for variable in iterable } exp should be in the form k and v pairs

n=int(input("enter a number"))
print("prime") if len([i for i in range(1,n+1) if n%i==0])==2 else print("not prime")
