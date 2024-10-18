
def myFun1():
    global x
    x=10
    print("Fun1 : x val is : ",x)

def myFun2():
    print("Fun2 : x val is : ",x)

#calling
myFun1()
myFun2()
print("Outside : x val is : ",x)
