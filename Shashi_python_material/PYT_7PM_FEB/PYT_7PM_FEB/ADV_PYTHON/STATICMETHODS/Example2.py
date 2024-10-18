
class Test:
    @staticmethod
    def method1():
        print("Static mtd1")

    def method2(self):
        print("Ins mtd-2 of Test")
        self.method1()
        Test.method1()

''' calling '''
t=Test()
t.method1()
Test.method1()

t.method2()
