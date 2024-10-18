import time
 
def mySum(*x):
    time.sleep(1)
    print("Type is : ",type(x))
    print("data is : ",x)
    s=0
    for i in x:
        s=s+i    
    print("Sum is : ",s)
    print("----------------------------")

#calling
mySum(10,20,30,40,50,60,70,80)
mySum(10,20,30,40)
mySum(10,20)
mySum(10)
mySum()
