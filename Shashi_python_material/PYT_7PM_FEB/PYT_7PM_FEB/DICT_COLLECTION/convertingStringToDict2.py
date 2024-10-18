s="ravi=23, roja=12"
print("string : ",s)

#S.split([chars]) -> list
#D.update({k:d})
lst=s.split(",") #['ravi=23','roja=12']
'''
stu={}
for i in lst:
    lst2=i.split("=") #['roja','12']
    k,d=lst2 #k=roja , d=12
    stu.update({k:int(d)})
print("Result is : ",stu)
'''

stu={}
for i in s.split(","):
    k,d=i.split("=")
    stu.update({k:int(d)})
    
print(stu)





    
    
    


