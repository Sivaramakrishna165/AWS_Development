
class SuperClass:
    @classmethod
    def method1(cls):
        print("cls mtd-1 of SuperClass")

class SubClass:
    def method2(self):
        SuperClass.method1()
        sa=SuperClass()
        sa.method1()
        print("Ins mtd-2 of SubClass")

#calling
sb=SubClass()
sb.method2()
    
