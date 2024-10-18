

import threading

def myFun():
    ct=threading.current_thread()
    tname=ct.name
    print(tname,"started its execution ....")

#calling
t1=threading.Thread(target=myFun,name="Child-1")
t2=threading.Thread(target=myFun,name="Child-2")
t1.start( )
t2.start( )
