
class SuperClass:
    def method1(self):
        print("Ins mtd-1 of SuperCls")

class SubClass:
    def method2(self):        
        sa=SuperClass()
        sa.method1()
        print("Ins mtd-2 of Subclass")

#calling
sb=SubClass()
sb.method2()
