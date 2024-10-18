import threading

def myFun():
    for i in range(1,11):
        print("myFun ... ",i)

#calling
t1=threading.Thread(target=myFun)
#name=t1.getName()
tname=t1.name
print("Thread Name is : ",tname)

#t1.setName("chinni")
t1.name="chinni"
tname=t1.name
print("Thread Name is : ",tname)

'''Note : Whenever u define any thread by default
every thread is created with default names i.e
Thread-1 | Thread-2 ....

Based on the application req, we can set or get the
name of thread.

In Previous versions
    getName( ) -> str
    setName(str)

In Latest Version we have to use name attribute or
  Property   '''
    
    

    





