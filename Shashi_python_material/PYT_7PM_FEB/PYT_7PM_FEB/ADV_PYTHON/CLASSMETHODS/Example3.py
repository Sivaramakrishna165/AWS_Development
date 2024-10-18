
class Test:
    def method1(self):
        print("Int mtd-1")
        print("self : \n",self)
        print("=============")

    @classmethod
    def method2(cls):
        print("cls mtd-2")
        print("cls : \n",cls)

#calling
t=Test()
t.method1()
Test.method2()
