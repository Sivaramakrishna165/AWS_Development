import time
import threading

def myFun():
    ct=threading.current_thread()
    print(t1.name," started its execution ....")
    time.sleep(5)
    print(t1.name," ends its execution .....")

#calling
t1=threading.Thread(target=myFun,name="Child-1")
t1.start()

b=t1.is_alive()
print("t1 isalive ? : ",b)

time.sleep(10)
print("t1 isalive ? : ",t1.is_alive())



          

