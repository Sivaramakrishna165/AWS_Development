import time
import threading

def sq(x):
    for i in x:
        time.sleep(1)
        s=i*i
        print("SQ ::: ",s)

def cu(x):
    for i in x:
        time.sleep(1)
        c=i*i*i
        print("CU ::: ",c)

#calling
lst=[1,2,3,4,5,6,7,8,9,10]
st=time.time()

t1=threading.Thread(target=sq,args=(lst,))
t2=threading.Thread(target=cu,args=(lst,))

t1.start()
t2.start()

t1.join()
t2.join()

et=time.time()
tt=et-st
print("total time : ",tt)





