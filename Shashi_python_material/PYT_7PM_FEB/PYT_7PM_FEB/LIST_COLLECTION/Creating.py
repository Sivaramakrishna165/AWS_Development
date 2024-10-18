
lst=[]
print("List : ",lst)
print("-------------------------------------")

lst2=[10,12.12,10,"Shashi",None,"Python"]
print("List : ",lst2)
print("-------------------------------------")

#list( ) -> list object
lst3=list()
print("List : ",lst3)
print("-------------------------------------")

#list(iterable) -> list object
t=(10,20,3.3,"Python")
print("Type is : ",type(t))
print("tuple is : ",t)
lst4=list(t)
print("Result is : ",lst4)
print("-------------------------------------")

#str to list
s="welcome"
print("string : ",s)
lst5=list(s)
print("Result is : ",lst5)
print("-------------------------------------")

#dict to list
stu={"sno":101,"sname":"ravi"}
print("Dict : ",stu)
lst6=list(stu)
print("Result is : ",lst6)
print("-------------------------------------")

#S.split( ) -> list
s="have a nice day"
lst7=s.split( )
print("Result is : ",lst7)
print("-------------------------------------")

#range(start,stop[,step]) -> range object | iterable
lst8=list( range(1,1001) )
print("Result is : ",lst8)















