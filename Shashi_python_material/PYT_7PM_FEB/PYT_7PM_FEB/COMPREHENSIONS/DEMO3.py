




#comprehensions
#Syn: [ <exp> for variable in iterable if test ]
#Syn: ( <exp> for variable in iterable )
#Syn: { <exp> for variable in iterable }
#Syn  { <exp> for variable in iterable } exp should be in the form k and v pairs

'''
lst2=[]
for i in range(0,21,2):
    lst2.append(i)
print("list : ",lst2)
'''
lst2=[i for i in range(0,21,2)]
print("list : ",lst2)
print("========================")

'''
lst=[]
for i in range(0,21):
    if i%2==0:
        lst.append(i)
print("list : ",lst) '''
lst=[i for i in range(0,21) if i%2==0]
print("List : ",lst)


















