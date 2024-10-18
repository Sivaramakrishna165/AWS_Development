import threading

def myFun():
    for i in range(1,11):
        print("myFun ... ",i)
        
''' calling '''
t1=threading.Thread(target=myFun,name="chinni")
tname=t1.name
print("Thread Name is : ",tname)

