
import time

def myFun(*x):
    time.sleep(1)
    print("Type is : ",type(x))
    print("Data is : ",x)
    s=0
    for i in x:
        s=s+i
    print("Sum is : ",s)
    print("=====================")

''' calling '''
myFun(10,20,30,40,50)
myFun(10,20,30)
myFun(10,20)
myFun(10)
myFun()
