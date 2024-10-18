import time

class Maths:
    def mySum(self,*x):
        time.sleep(.2)
        s=0
        for i in x:
            s=s+i
        print("Sum is : ",s)
        print("=============")

#calling
m=Maths()
m.mySum(10,20,30,40,50,60,70)
m.mySum(10,20,30,40)
m.mySum(10,20)
m.mySum(10)
m.mySum()


