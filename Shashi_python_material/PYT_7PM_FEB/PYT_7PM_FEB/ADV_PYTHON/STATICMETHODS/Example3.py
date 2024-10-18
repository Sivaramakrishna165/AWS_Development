
class Test:
    def method1(self):
        print("Inst mtd-1")

    @classmethod
    def method2(cls):
        print("Cls mtd-2 ")

    @staticmethod
    def method3(x,y):
        print("static mtd-3")
        print("x val is : ",x)
        print("y val is : ",y)

#calling
t=Test()
t.method1()
Test.method2()
Test.method3(10,20)
