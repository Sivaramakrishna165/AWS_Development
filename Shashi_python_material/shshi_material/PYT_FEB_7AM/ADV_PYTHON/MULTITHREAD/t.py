import threading

def myFun():
    for i in range(1,11):
        print("myFun ... ",i)

#calling
''' t1=threading.Thread(target=myFun)
    t1.name="Child" '''

t1=threading.Thread(target=myFun,name="Child")
tname=t1.name
print("Thread Name is : ",tname)

