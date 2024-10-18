import threading
import time

def myFun1():
    for i in range(1,11):
        time.sleep(2)
        print("MyFun1.... ",i)

def myFun2():
    for i in range(20,31):
        print("MyFun2 >>> ",i)

''' Calling '''
t1=threading.Thread(target=myFun1)
t2=threading.Thread(target=myFun2)
t1.start()
t1.join()
t2.start()
