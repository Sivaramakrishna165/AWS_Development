import threading
import time

def myFun():
    ct=threading.current_thread()
    print(ct.name," Started its Execution ....")
    time.sleep(5)
    print(ct.name," Ends its Execution ....")

#calling
t1=threading.Thread(target=myFun,name="Child-1")
t2=threading.Thread(target=myFun,name="Child-2")
t1.start()
t2.start()

atc=threading.active_count()
print("Active Thread Count : ",atc)

time.sleep(7)
atc=threading.active_count()
print("Active Thread Count : ",atc)








