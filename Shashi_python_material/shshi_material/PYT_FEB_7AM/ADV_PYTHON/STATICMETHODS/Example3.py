class Test:
    def method1(self):
        print("Ins mtd-1 of Test")

    @classmethod
    def method2(cls):
        print("cls mtd-2 of Test")

    @staticmethod
    def method3(x,y):
        print("static mtd-3 of Test")
        s=x+y
        print("sum is : ",s)

#calling
t=Test()
t.method1()
Test.method2()
Test.method3(10,20)


