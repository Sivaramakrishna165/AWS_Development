



'''
[<expression> for variable in iterable if test]
(<expression> for variable in iterable)
{<expression> for variable in iterable}
{<expression> for variable in iterable}
    here expression should be in the form key and value
'''
lst=[]
for i in range(1,41):
    if i%2==0:
        lst.append(i)
        
print("Even  : ",lst)
print("===========================")

lst3=[i for i in range(1,41) if i%2==0]
print("Even : ",lst3)
print("===========================")


#list(iterable) -> list 
lst2=list( range(2,41,2) )
print("Even : ",lst2)
print("===========================")
#OR
lst3=[i for i in range(2,41,2)]
print("Even : ",lst3)
















