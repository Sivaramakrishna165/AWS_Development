
import time
def myFun(a,b,/,c,d,*,e,f):
    time.sleep(1)
    print("a : ",a)
    print("b : ",b)
    print("c : ",c)
    print("d : ",d)
    print("e : ",e)
    print("f : ",f)
    print("===============")

''' calling
a,b - positional only
c,d - positional or keyword
e,f  - keyword only args'''
myFun(10,20,30,40,e=50,f=70)
myFun(10,20,c=30,d=40,e=50,f=60)
#myFun(10,20,c=30,d=40,50,60) Error



