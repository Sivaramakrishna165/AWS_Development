
#string to dict
#S.split( ) -> list
#D.fromkeys(iterable,value=None)

s="nani mani sony bunny"
print("string : ",s)

lst=s.split() #['nani','mani'.,.....]
stu={}
stu=stu.fromkeys(lst)
print("Dict : ",stu)
