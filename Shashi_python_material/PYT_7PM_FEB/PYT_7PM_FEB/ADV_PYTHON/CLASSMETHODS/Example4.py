
class Test:
    y=20
    def method1(self):
        print("Ins mtd-1 of Test")
        self.x=10
        print("Ins x val is : ",self.x)
        print("static y val is : ",Test.y)

    @classmethod
    def method2(cls):
        print("Cls mtd-2 of Test")
        #print("x val is : ",self.x) NE
        print("static y val is : ",Test.y)
        print("static y val is : ",cls.y)

#calling
t=Test()
t.method1()
Test.method2()
