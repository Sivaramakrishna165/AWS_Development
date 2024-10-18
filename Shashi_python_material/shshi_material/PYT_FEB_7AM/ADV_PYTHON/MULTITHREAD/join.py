
import threading
import time

def myFun():
    for i in range(1,11):
        time.sleep(2)
        print("myFun ... ",i)

#calling
t1=threading.Thread(target=myFun)
t1.start()
t1.join()

for i in range(20,31):
    print("Main >>> ",i)
