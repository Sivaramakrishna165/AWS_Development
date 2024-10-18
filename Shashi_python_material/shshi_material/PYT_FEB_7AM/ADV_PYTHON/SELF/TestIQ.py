
class Test:
    def method1(self):
        print("mtd-1 of Test")
        print(self)
        print("=====================")

    def method2(x,y):
        print("mtd-2 of Test")
        print("x val is : \n ",x)
        print("y val is : ",y)
        print("=====================")

    def method3(shashi,khanna):
        print("mtd-3 of Test")
        print("shashi : \n ",shashi)
        print("khanna : ",khanna)

#calling
t=Test()
t.method1()
t.method2(123)
t.method3(222)

    
