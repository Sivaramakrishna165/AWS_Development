

#comprehensions
#Syn: [ <exp> for variable in iterable ]
#Syn: ( <exp> for variable in iterable )
#Syn: { <exp> for variable in iterable }
#Syn  { <exp> for variable in iterable } exp should be in the form k and v pairs

'''
lst=[]
for i in range(1,101):
    lst.append(i)
print("List : ",lst)
'''
lst=[i for i in range(1,101)]
print("type is : ",type(lst))
print("Result is : ",lst)







