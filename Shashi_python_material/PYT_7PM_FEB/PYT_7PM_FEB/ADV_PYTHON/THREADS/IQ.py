
''' What is default Thread in Python ?
    which thread is executed by os
    implicitly ?  '''

import threading
def myFun():
    for i in range(1,11):
        print("myFun ... ",i)

''' calling '''
t1=threading.Thread(target=myFun)
t1.start()

for i in range(20,31):
    print("Main >>> ",i)
    
