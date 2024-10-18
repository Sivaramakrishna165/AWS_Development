
#        0                    1        2            
lst=["Ramesh","hyd",23]

print("List : ",lst)
'''
name=lst[0]
city=lst[1]
age=lst[2]
'''

name,city,age=lst
#name,city=lst ValueError :  Too many values to unpack
x=lst
print(name,city,age,sep=' -- ')
print("List : ",lst)
print("x : ",x)
