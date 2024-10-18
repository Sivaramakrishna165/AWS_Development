



'''
[<expression> for variable in iterable]
(<expression> for variable in iterable)
{<expression> for variable in iterable}
{<expression> for variable in iterable}
    here expression should be in the form key and value
'''

lst1=[1,2,3,4,5,6,7,8,9,10]
print("list ",lst1)
print("==================")

lst2=list( range(1,11) )
print("list : ",lst2)
print("==================")

lst3=[]
for i in range(1,11):
    lst3.append(i)
print("list : ",lst3)
print("==================")

lst4=[i for i in range(1,11)]
print("type is : ",type(lst4))
print("List : ",lst4)
print("==================")






























