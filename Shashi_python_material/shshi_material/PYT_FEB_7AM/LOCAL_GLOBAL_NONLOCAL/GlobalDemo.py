y=20 #global variable

def myFun1():
    x=10 #local variable
    print("From myFun1 ")
    print("x val is : ",x) #10
    print("y val is : ",y) #20
    print("=============")

def myFun2():
    print("From myFun2 ")
    #print("x val is : ",x)
    print("y val is : ",y)
    print("===============")

#calling
myFun1()
myFun2()
print("From outside of all the function")
print("y val is : ",y)