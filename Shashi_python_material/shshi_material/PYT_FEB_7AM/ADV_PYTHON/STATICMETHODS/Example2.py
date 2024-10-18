
class Test:
    @staticmethod
    def method1():
        print("static mtd-1 of Test")

    def method2(self):
        self.method1()
        Test.method1()
        print("Int mtd-2 of Test")

#calling
t=Test()
t.method2()

