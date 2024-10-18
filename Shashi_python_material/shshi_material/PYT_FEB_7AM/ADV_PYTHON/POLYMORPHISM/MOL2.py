
class Test:
    def method1(self):
        print("Ins mtd-1 of Test")

    def method1(self,x):
        print("Ins mtd-1 of Test ",x)

#calling
t=Test()
t.method1(123)
t.method1( )
