
class Test:
    y=20 #static variable
    def method1(self):
        self.x=10 #instance
        print("Ins mtd-1 of Test")
        print("Ins x val is : ",self.x)
        print("static y val is : ",Test.y)
        print("=====================")

    @classmethod
    def method2(cls):
        print("Cls mtd-2 of Test")
        print("static y val is : ",Test.y)
        print("static y val is : ",cls.y)
        #print("Ins x val is : ",self.x)

#calling
t=Test()
t.method1()
Test.method2()
