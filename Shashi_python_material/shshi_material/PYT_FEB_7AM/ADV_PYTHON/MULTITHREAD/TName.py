import threading

def myFun():
    for i in range(1,11):
        print("MyFun ... ",i)

#calling
t1=threading.Thread(target=myFun)
tname=t1.name  #In Old version t1.getName( )
print("Thread Name is : ",tname)

t1.name="Child" #In Old version t1.setName("child")
tname=t1.name  
print("Thread Name is : ",tname)
