l1=[]
print("Data is : ",l1)
print("===========")

l2=[10,12.12,None,10,10+20j,"shashi"]
print("Data is : ",l2)
print("=======================")

#list( ) -> list object
l3=list( )
print("Type is : ",type(l3))
print("Data is : ",l3)
print("=======================")

#list(iterable) -> list object
t=(10,20,30,1.1,2.2,3.3)
l4=list(t)
print("type is : ",type(l4))
print("Data is : ",l4)
print("=======================")

s="welcome"
l5=list(s)
print("Data is : ",l5)
print("=======================")

#range(start[,stop,step]) -> range object | iterable
l6=list( range(1,51,1) )
print("Data is : ",l6)
print("=======================")

#S.split([chars]) -> list
s="have a nice day"
print("data is : ",s)
l7=s.split()
print("Result is : ",l7)





























