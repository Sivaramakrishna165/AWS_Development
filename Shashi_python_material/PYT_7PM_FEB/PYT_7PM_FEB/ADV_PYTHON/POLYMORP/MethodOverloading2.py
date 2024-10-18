import time

class Test:
    def mySum(self,x=None,y=None,z=None):
        time.sleep(.2)
        if x!=None and y!=None and z!=None:
            s=x+y+z
            print("sum is : ",s)

        elif x!=None and y!=None:
            s=x+y
            print("sum is : ",s)

        elif x!=None:
            print("sum is : ",x)

        else:
            print("sum is : 0 ")

''' calling '''
t=Test()
t.mySum(10,20,30)
t.mySum(10,20)
t.mySum(10)
t.mySum()


