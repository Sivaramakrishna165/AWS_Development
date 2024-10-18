
import time

def mySum(x,y,z=30):
    time.sleep(1)
    s=x+y+z
    print("Sum is : ",s)
    print("==============")

''' calling '''
mySum(40,50,60)
mySum(50,60)
mySum(x=10,z=90,y=20)
    
