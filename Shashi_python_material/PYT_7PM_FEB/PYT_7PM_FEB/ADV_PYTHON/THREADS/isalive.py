import threading,time

def myFun():
    ct=threading.current_thread()
    print(ct.name,"started its execution ....")
    time.sleep(5)
    print(ct.name,"ends its execution ....")

#calling
t1=threading.Thread(target=myFun,name="child-1")
t1.start()
print("t1 is under execution ? : ",t1.is_alive())
time.sleep(10)
print("t1 is under execution ? : ",t1.is_alive())
