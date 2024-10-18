import time

def myFun(**stu):
    time.sleep(1)
    print("Type is : ",type(stu))
    print("Dict : ",stu)
    for k,d in stu.items():
        time.sleep(.2)
        print(k,d,sep=' >>> ')
    print("==================")

#calling
myFun(sno=101,sname="Ramesh",scity="Hyd")
myFun(sno=102,sname="Roja")
myFun(sno=103)
myFun()
