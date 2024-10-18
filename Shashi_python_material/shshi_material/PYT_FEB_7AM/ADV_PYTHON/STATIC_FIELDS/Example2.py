
class Test:
    x=10
    def method1(self):
        x=20
        self.x=30
        print("x val is : ",x)
        print("x val is : ",self.x)
        print("x val is : ",Test.x)

#calling
t=Test( )
t.method1()
