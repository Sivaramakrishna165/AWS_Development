#app1.py
import threading

def myFun():
    for i in range(1,11):
        print("MyFun ... ",i)

def myFun2():
    for i in range(20,31):
        print("MyFun2 ... ",i)

#calling
t1=threading.Thread(target=myFun)
t2=threading.Thread(target=myFun2)
t1.start( )
t2.start( )
