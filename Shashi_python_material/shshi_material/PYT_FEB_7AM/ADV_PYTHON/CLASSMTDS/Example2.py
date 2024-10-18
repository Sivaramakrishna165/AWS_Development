
class Test:
    @classmethod
    def method1(cls):
        print("cls mtd-1 of Test")

    def method2(self):
        self.method1()
        Test.method1()
        print("ins mtd-2 of Test")

#calling
t=Test()
t.method2()
