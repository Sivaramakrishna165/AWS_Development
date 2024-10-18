
import time

def myFun(**stu):
    time.sleep(.2)
    print("Type is : ",type(stu))
    print("Data is : ",stu)
    for k,d in stu.items():
        time.sleep(.2)
        print(k,d,sep=' >>> ')
    print("==================")

''' calling '''
myFun(sno=101,sname="Rajesh",scity="hyd")
myFun(sno=102,sname="Rams")
myFun(sno=103)
myFun()
