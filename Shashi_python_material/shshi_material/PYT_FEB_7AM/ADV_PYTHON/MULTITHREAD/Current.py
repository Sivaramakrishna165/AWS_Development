



import threading

ct=threading.current_thread()
tname=ct.name
print("Current Thread name is : ",tname)
