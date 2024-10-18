
import threading

def myFun():
    ct=threading.current_thread()
    tname=ct.name
    print(tname,"started its execution.... ")

#calling
t1=threading.Thread(target=myFun,name="child")
t1.start()

t2=threading.Thread(target=myFun,name="Child-2")
t2.start()

#main
ct=threading.current_thread()
tname=ct.name
print("Thread Name is : ",tname)




