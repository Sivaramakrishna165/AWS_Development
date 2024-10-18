
class Test:
    def method1(self):
        print("ins mtd-1 of Test")
        print("self : ",self)
        print("========================")

    @classmethod
    def method2(cls):
        print("cls mtd-2 of Test")
        print("cls : ",cls)

#calling
t=Test()
t.method1()
Test.method2()
