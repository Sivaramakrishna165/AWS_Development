

import threading

def myFun():
    tn=threading.current_thread().name
    print(tn,"started its execution...")
    mt.join()
    print(tn,"ends its execution ....")

#calling
mt=threading.current_thread() #MainThread
print(mt.name,"Started Its execution ....")

t1=threading.Thread(target=myFun,name="child-1")
t1.start()
t1.join()
print(mt.name,"ends its execution ...")

