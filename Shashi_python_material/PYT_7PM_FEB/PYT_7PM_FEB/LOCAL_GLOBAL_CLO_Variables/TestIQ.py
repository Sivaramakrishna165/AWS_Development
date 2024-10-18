
x=10

def myFun():
    global x
    x=x+10
    print("myFun : ",x)

#calling
myFun()
print("From outside :")
print("x val is : ",x)

'''Note: if u want perform any operation on the global
variable in the function scope,we must tell the pvm
to treat that variable as global  by using global
keyword otherwise it will treated as local variable
without a value thus it will raise UnboundLocalError '''

