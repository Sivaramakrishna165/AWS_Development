import time

def sq(x):
    for i in x:
        time.sleep(1)
        s=i*i
        print("SQ ::::: ",s)

def cu(x):
    for i in x:
        time.sleep(1)
        c=i*i*i
        print("CU >>>> ",c)

#calling
lst=[1,2,3,4,5,6,7,8,9,10]
st=time.time()
sq(lst)
cu(lst)
et=time.time()
tt=et-st
print("total time : ",tt)




