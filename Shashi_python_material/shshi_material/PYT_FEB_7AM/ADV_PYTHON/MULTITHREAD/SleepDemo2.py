
import threading
import time

def myFun():
    for i in range(1,11):
        print("myFun....",i)

#calling
t1=threading.Thread(target=myFun,name="child")
t1.start()

time.sleep(10)
for i in range(20,31):
    print("Main .... ",i)
