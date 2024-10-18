def myFun1():
    for i in range(1,11):
        print("MyFun1 .... ",i)

def myFun2():
    time.sleep(10)
    for i in range(20,31):
        print("MyFun2 ... ",i)

#calling
import threading
import time
t1=threading.Thread(target=myFun1)
t2=threading.Thread(target=myFun2)
t1.start()
t2.start()
for i in range(30,41):
    print("Main >>> ",i)
