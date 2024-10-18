
import threading

def myFun():
    ct=threading.current_thread()
    print(ct.name," started its execution ....")
    mt.join()
    print(ct.name," ends its execution ....")

#calling
mt=threading.current_thread() #MainThread
print(mt.name," started its execution ....")

t1=threading.Thread(target=myFun,name="Child")
t1.start()
t1.join()
print(mt.name," Ends its Execution....")

