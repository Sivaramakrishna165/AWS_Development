import time
class Test:
    def __init__(self):
        print("const is invoked ...")
        self.x=10
        self.y=20

    def getData(self):
        print("x val is : ",self.x)
        print("y val is : ",self.y)
        print("===============")

    def __del__(self):
        time.sleep(.5)
        print("Dest Is Invoked")
        print("Object is Deleted ...")
        print("R D. A. Done...")
        print("* * * *  *  * * * * * * * * * * *")

#calling
t1=Test()
t1.getData( )
t1=None

t2=Test()
print("Data From t2")
t2.getData( )
t2=None





    
