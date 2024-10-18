
import time

class Maths:
    def mySum(self,x=None,y=None,z=None):
        time.sleep(1)
        if x!=None and y!=None and z!=None:
            s=x+y+z
            print("Sum is : ",s)
        elif x!=None and y!=None:
            s=x+y
            print("Sum is : ",s)
        elif x!=None:
            print("Sum is : ",x)
        else:
            print("Sum is : 0 ")

#calling
m=Maths()
m.mySum(10,20,30)
m.mySum(10,20)
m.mySum(10)
m.mySum()
