
class Test:
    def method1(self):
        x=10
        self.y=20
        print("mtd-1 x val is : ",x)
        print("mtd-1 y val is : ",self.y)
        print("====================")

    def method2(self):
        #print("mtd-2 x val is : ",x)
        print("mtd-2 y val is :",self.y)

#calling
t=Test()
t.method1()
t.method2()





