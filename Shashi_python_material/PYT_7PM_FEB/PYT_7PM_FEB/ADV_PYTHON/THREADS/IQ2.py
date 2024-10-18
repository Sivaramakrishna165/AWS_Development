



#How to get object current working Thread

import threading
cwt=threading.current_thread()
tname=cwt.name
print("Thread Name is : ",tname)
