
x=20

def myFun():
    global x
    x=10
    print("myFun : ",x)
    print("===========")

def myFun2():
    print("myFun2 : ",x)
        

#calling
myFun()
myFun2( )
print("From outside :")
print("x val is : ",x)

'''Note: if u want perform any operation on the global
variable in the function scope,we must tell the pvm
to treat that variable as global  by using global
keyword otherwise it will treated as local variable
without a value thus it will raise UnboundLocalError '''

