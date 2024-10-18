
s="ravi roja srija"
print("string : ",s)

#S.split([char]) -> list
#List to dict collection by using fromkeys
#D.fromkeys(iterable,value=None) -> dict
'''
stu={}
lst=s.split()
stu=stu.fromkeys(lst)
print("Result is : ",stu)
'''
stu={}.fromkeys(s.split())
print("Result is : ",stu)
