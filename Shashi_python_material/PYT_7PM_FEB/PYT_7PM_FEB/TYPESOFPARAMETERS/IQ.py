'''
def myFun(x,y,*z):
    print("x : ",x)
    print("y : ",y)
    print("z : ",z)
    print("=============")

#calling
myFun(10,20,40,50,60,70)
'''

def myFun(*x,y,z):
    print("x : ",x)
    print("y : ",y)
    print("z : ",z)
    print("=============")

myFun(10,20,30,40,50,y=90,z=99)










    


