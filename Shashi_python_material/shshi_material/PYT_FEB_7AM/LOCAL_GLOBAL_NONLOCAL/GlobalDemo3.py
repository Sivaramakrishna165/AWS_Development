x=10

def myFun():
    global x
    x=x+10
    print("x val is : ",x)

#calling
myFun()
print("x val is : ",x)
