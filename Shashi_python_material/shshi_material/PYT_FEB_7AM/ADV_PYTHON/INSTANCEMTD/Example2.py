
class Test:
    def method1(self):
        print("Mtd-1 of Test")

    def method2(self):
        self.method1()
        print("Mtd-2 of Test")

#calling
t=Test()
t.method2()
