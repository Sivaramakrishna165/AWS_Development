import time

class Test:
    def mySum(self,*x):
        time.sleep(1)
        print("Elements : ",x)
##        s=0
##        for i in x:
##            s=s+i        
        print("Sum is : ",sum(x))
        print("===============")

''' calling '''
t=Test()
t.mySum(10,20,30,40,50,60)
t.mySum(10,20,30,40)
t.mySum(10,20,30)
t.mySum(10,20)
t.mySum(10)
t.mySum()
        
