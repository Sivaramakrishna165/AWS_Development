
class SuperClass:
    @staticmethod
    def method1():
        print("static mtd-1 of SuperClass")

class SubClass:
    def method2(self):
        SuperClass.method1()
        sa=SuperClass()
        sa.method1()
        print("Ins mtd-2 of Subclass")

#calling
sb=SubClass( )
sb.method2()
