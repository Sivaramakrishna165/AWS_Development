import threading
import time

def myFun():
    tn=threading.current_thread().name
    print(tn,"started its execution ....")
    time.sleep(5)

#calling
t1=threading.Thread(target=myFun,name="child-1")
t1.start()
print("Tname : ",t1.name)
print("TID : ",t1.ident)

t2=threading.Thread(target=myFun,name="child-2")
t2.start()
print("Tname : ",t2.name)
print("TID : ",t2.ident)

