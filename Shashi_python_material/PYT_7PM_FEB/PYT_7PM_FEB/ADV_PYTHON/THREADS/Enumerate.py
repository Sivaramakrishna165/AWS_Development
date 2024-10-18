
import threading
import time

def myFun():
    tn=threading.current_thread().name
    print(tn," started its execution ....")
    time.sleep(5)
    print(tn," ends its execution ....")

def myFun2():
    tn=threading.current_thread().name
    print(tn," started its execution ....")
    time.sleep(5)
    print(tn," ends its execution ....")

#calling
t1=threading.Thread(target=myFun,name="child-1")
t2=threading.Thread(target=myFun2,name="child-2")
t1.start()
t2.start()

print("Active Thread Count : ",threading.active_count())
lst=threading.enumerate()

for t in lst:
    time.sleep(.2)
    print("Thread Name : ",t.name)

time.sleep(10)
print("Active Thread Count : ",threading.active_count())

lst=threading.enumerate()
for t in lst:
    time.sleep(.2)
    print("Thread Name : ",t.name)


