
#string to dict
#S.split( ) -> list


s="Ramesh=23,Nani=27"
print("String : ",s)

stu={}
lst=s.split(",") #['Ramesh=23','Nani=27']

for i in lst:
    k,d=i.split("=")
    stu.update({k:int(d)})

print("Dict : ",stu)




