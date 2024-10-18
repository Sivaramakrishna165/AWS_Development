import time

'''
def myFun1(*x,*y):   Invalid | SyntaxError
    pass
'''

'''
def myFun1(**x,**y):
    pass
'''

def myFun1(name,*marks):
    pass
    

def myFun(*x,**y):
    time.sleep(1)
    print("x val is : ",x)
    print("y val is: ",y)
    print("===============")

#calling
myFun(10,20,30,40,50,sno=101,sname="ramesh")
