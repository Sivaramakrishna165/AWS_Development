
import threading
import time

def myFun():
    ct=threading.current_thread()
    print(ct.name," started its execution ....")
    time.sleep(10)
    print(ct.name," ends its execution .....")

#calling
t1=threading.Thread(target=myFun,name="Child-1")
t2=threading.Thread(target=myFun,name="Child-2")
t1.start()
t2.start()

print("Active_Count : ",threading.active_count())
lto=threading.enumerate()

for t in lto:
    time.sleep(.2)
    print("Thread Name ",t.name)








