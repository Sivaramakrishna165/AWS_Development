



'''
[<expression> for variable in iterable]
(<expression> for variable in iterable)
{<expression> for variable in iterable}
{<expression> for variable in iterable}
    here expression should be in the form key and value
'''

#input() -> str
#S.split([chars]) -> list

'''
data=input("Enter 3 numbers ")
lst=data.split()
m1,m2,m3=lst
t=int(m1)+int(m2)+int(m3)
print("sum is : ",t)
print("===========================")

#App-2
m1,m2,m3=[int(i) for i in input("Enter 3 numbers").split()]
t=m1+m2+m3
print("Sum is : ",t)
'''

#sum(iterable)
print("Sum is : ",sum([int(i) for i in input("Enter 3 numbers").split()]))










































