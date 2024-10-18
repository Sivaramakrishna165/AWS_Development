import threading

def myFun1():
    for i in range(1,11):
        print("myFun ... ",i)

#Calling
t1=threading.Thread(target=myFun1)
t1.start( )

for i in range(20,31):
    print("Main >>>> ",i)
