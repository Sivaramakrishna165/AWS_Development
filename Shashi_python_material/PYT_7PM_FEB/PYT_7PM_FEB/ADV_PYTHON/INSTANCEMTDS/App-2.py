
class Test:
    def method1(self):
        print("Ins mtd-1 ")

    def method2(self):
        self.method1()
        print("Ins mtd-2 ")

#calling
t=Test()
t.method2()
    
